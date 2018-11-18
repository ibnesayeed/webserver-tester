#!/usr/bin/env python3

from flask import Flask, Response
from flask import render_template, abort, request

import os
import re
import requests
import docker
import json
import base64

from tester import HTTPTester

# This should be changed inline or supplied via the environment variable each semester the course is offered
COURSEREPO = os.getenv("COURSEREPO", "phonedude/cs531-f18")
COURCEID = os.getenv("COURCEID", "cs531")
# This is needed if student repos are kept private (ideally, supply it via the environment variable)
CREDENTIALS = os.getenv("GITHUBKEY", "")

student_repos = {}


app = Flask(__name__)
client = docker.from_env()

try:
    client.ping()
    DEPLOYER = True
    print("Docker daemon is connected, enabling deployment")
except Exception as e:
    DEPLOYER = False
    print("Docker daemon is not reachable, disabling deployment")


def generate_test_cases_json(test_batches):
    test_cases = []
    for batch, tests in test_batches.items():
        for fname, func in tests.items():
            test_cases.append({"id": fname, "description": func.__doc__, "batch": batch})
    return json.dumps(test_cases)

default_tester = HTTPTester()
batch_numbers = default_tester.test_batches.keys()
test_cases = generate_test_cases_json(default_tester.test_batches)


def extract_repo_from_url(github_url):
    repo = re.sub("\.git$", "", github_url)
    match = re.search("github.com[:/]([^/]+)/([^/]+)", repo)
    if match is not None:
        return f"{match[1]}/{match[2]}"
    print(f"{github_url} is not a recognized GitHub URL")
    return None


def fetch_student_repo(csid):
    url = f"https://raw.githubusercontent.com/{COURSEREPO}/master/users/{csid}"
    try:
        req = requests.get(url)
        if req.status_code == 200:
            student_repos[csid] = extract_repo_from_url(req.text.strip())
            return student_repos[csid]
    except Exception as e:
        print(f"Cannot fetch repo URI from GitHub: {e}")
    return None


def get_student_repo(csid):
    return student_repos.get(csid, fetch_student_repo(csid))


def get_authorized_repo_url(repo):
    if repo is None:
        return None
    cred = CREDENTIALS + "@" if CREDENTIALS else ""
    return f"https://{cred}github.com/{repo}.git"


def jsonify_result(result):
    result["res"]["payload"] = base64.b64encode(result["res"]["payload"]).decode() if result["res"]["payload"] else ""
    return json.dumps(result) + "\n"


@app.route("/")
def home():
    return render_template("index.html", test_batches=batch_numbers, student_ids=student_repos.keys(), show_deployer=DEPLOYER, courseid=COURCEID)


@app.route("/servers/deploy/<csid>", strict_slashes=False, defaults={"gitref": ""})
@app.route("/servers/deploy/<csid>/<gitref>")
def deploy_server(csid, gitref):
    csid = csid.strip()
    repo = get_student_repo(csid)
    if repo is None:
        return Response(f"User record `{csid}` not present in `https://github.com/{COURSEREPO}/tree/master/users`.", mimetype="text/plain", status=404)

    msgs = []
    contname = f"{COURCEID}-{csid}"
    imgname = f"{COURCEID}/{csid}"
    repo_url = get_authorized_repo_url(repo)
    if gitref:
        imgname += f":{gitref}"
        repo_url += f"#{gitref}"

    buildimg = True
    if request.args.get("rebuild") == "skip":
        try:
            client.images.get(imgname)
            buildimg = False
        except Exception as e:
            msgs.append(f"Image `{imgname}` is not present.")

    if buildimg:
        try:
            print(f"Building image {imgname}")
            client.images.build(path=repo_url, tag=imgname)
            msgs.append(f"Image `{imgname}` built from the `{gitref if gitref else 'master'}` branch/tag of the `https://github.com/{repo}` repo.")
        except Exception as e:
            return Response(f"Building image `{imgname}` from the `{repo}` repo failed, ensure that the repo is accessible and contains a valid `Dockerfile`. Response from the Docker daemon: {str(e).replace(CREDENTIALS + '@', '')}", mimetype="text/plain", status=500)
    else:
        msgs.append(f"Reusing existing image `{imgname}` to redeploy the service.")

    try:
        print(f"Removing existing container {contname}")
        client.containers.get(contname).remove(v=True, force=True)
        msgs.append("Related existing container removed.")
    except Exception as e:
        print(f"Container {contname} does not exist")

    try:
        print(f"Running new container {contname} using {imgname} image")
        client.containers.run(imgname, detach=True, network=COURCEID, name=contname)
        msgs.append(f"A new container is created and the service `{contname}` is deployed successfully.")
    except Exception as e:
        return Response(f"Service deployment failed. Response from the Docker daemon: {e}", mimetype="text/plain", status=500)

    return Response(" ".join(msgs), mimetype="text/plain", status=200)


@app.route("/servers/destroy/<csid>", strict_slashes=False)
def server_destroy(csid):
    csid = csid.strip()
    repo = get_student_repo(csid)
    if repo is None:
        return Response(f"Unrecognized student `{csid}`.", mimetype="text/plain", status=404)

    contname = f"{COURCEID}-{csid}"
    try:
        print(f"Removing existing container {contname}")
        client.containers.get(contname).remove(v=True, force=True)
        return Response(f"Server `{contname}` destroyed successfully.", mimetype="text/plain", status=200)
    except Exception as e:
        print(f"Container {contname} does not exist")
        return Response(f"Server `{contname}` does not exist.", mimetype="text/plain", status=404)


@app.route("/servers/logs/<csid>", strict_slashes=False)
def server_logs(csid):
    csid = csid.strip()
    repo = get_student_repo(csid)
    if repo is None:
        return Response(f"Unrecognized student `{csid}`.", mimetype="text/plain", status=404)

    contname = f"{COURCEID}-{csid}"
    try:
        print(f"Finding an existing container {contname}")
        cont = client.containers.get(contname)
        return Response(cont.logs(stream=True), mimetype="text/plain")
    except Exception as e:
        print(f"Container {contname} does not exist")
        return Response(f"Server `{contname}` does not exist.", mimetype="text/plain", status=404)


@app.route("/tests", strict_slashes=False)
def list_tests():
    return Response(test_cases, mimetype="application/json")


@app.route("/tests/<hostport>/test_<int:batch>_<tid>")
def run_test(hostport, batch, tid):
    try:
        t = HTTPTester(hostport)
    except ValueError as e:
        return Response(f"{e}", status=400)
    test_id = f"test_{batch}_{tid}"
    try:
        result = t.run_single_test(test_id)
        return Response(jsonify_result(result), mimetype="application/json")
    except Exception as e:
        return Response(f"{e}", status=404)


@app.route("/tests/<hostport>", strict_slashes=False, defaults={"batch": ""})
@app.route("/tests/<hostport>/<int:batch>")
def run_tests(hostport, batch):
    try:
        t = HTTPTester(hostport)
    except ValueError as e:
        return Response(f"{e}", status=400)
    batch = str(batch)
    if batch and batch not in t.test_batches.keys():
        return Response(f"Assignment `{batch}` not implemented", status=404)
    batches = [batch] if batch else t.test_batches.keys()

    def generate():
        for batch in batches:
            for result in t.run_batch_tests(batch):
                yield jsonify_result(result)

    return Response(generate(), mimetype="application/ors")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000")
