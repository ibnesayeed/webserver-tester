#!/usr/bin/env python3

from flask import Flask, Response
from flask import render_template, abort, request

import os
import re
import requests
import docker
import json
import base64

from servertester.base.httptester import HTTPTester
from servertester.testsuites import *

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


def generate_test_cases_json():
    test_cases = []
    for sname, suite in testsuites.items():
        for fname, func in suite().testcases.items():
            test_cases.append({"id": fname, "description": func.__doc__, "suite": sname})
    return json.dumps(test_cases)

test_cases = generate_test_cases_json()


def extract_repo_from_url(github_url):
    repo = re.sub("\.git$", "", github_url)
    match = re.search("github.com[:/]([^/]+)/([^/]+)", repo)
    if match is not None:
        return f"{match[1]}/{match[2]}"
    return None


def fetch_student_repo(csid):
    url = f"https://raw.githubusercontent.com/{COURSEREPO}/master/users/{csid}"
    try:
        req = requests.get(url)
        if req.status_code == 200:
            student_repos[csid] = extract_repo_from_url(req.text.strip())
            return student_repos[csid]
    except Exception as e:
        pass
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
    return render_template("index.html", test_batches=testsuites.keys(), student_ids=student_repos.keys(), show_deployer=DEPLOYER, courseid=COURCEID)


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
            msgs.append(f"Image `{imgname}` is not present")

    if buildimg:
        try:
            msgs.append(f"Cloning the `https://github.com/{repo}.git` repo and checking the `{gitref if gitref else 'master'}` branch/tag out")
            img, logs = client.images.build(path=repo_url, tag=imgname)
            msgs.append("".join([l.get("stream", "") for l in logs]))
        except Exception as e:
            msgs.append(str(e).replace(CREDENTIALS + '@', ''))
            msgs.append(f"Building image `{imgname}` failed")
            msgs.append("Ensure that the repo is accessible and contains a valid `Dockerfile`")
            return Response("\n".join(msgs), mimetype="text/plain", status=500)
    else:
        msgs.append(f"Reusing existing image `{imgname}` to redeploy the service")

    try:
        client.containers.get(contname).remove(v=True, force=True)
        msgs.append("Related existing container removed")
    except Exception as e:
        pass

    try:
        client.containers.run(imgname, detach=True, network=COURCEID, name=contname)
        msgs.append(f"A new container is created and the server `{contname}` is deployed successfully")
    except Exception as e:
        msgs.append(str(e))
        msgs.append("Service deployment failed")
        return Response("\n".join(msgs), mimetype="text/plain", status=500)

    return Response("\n".join(msgs), mimetype="text/plain", status=200)


@app.route("/servers/destroy/<csid>", strict_slashes=False)
def server_destroy(csid):
    csid = csid.strip()
    repo = get_student_repo(csid)
    if repo is None:
        return Response(f"Unrecognized student `{csid}`.", mimetype="text/plain", status=404)

    contname = f"{COURCEID}-{csid}"
    try:
        client.containers.get(contname).remove(v=True, force=True)
        return Response(f"Server `{contname}` destroyed successfully.", mimetype="text/plain", status=200)
    except Exception as e:
        return Response(f"Server `{contname}` does not exist.", mimetype="text/plain", status=404)


@app.route("/servers/logs/<csid>", strict_slashes=False)
def server_logs(csid):
    csid = csid.strip()
    repo = get_student_repo(csid)
    if repo is None:
        return Response(f"Unrecognized student `{csid}`.", mimetype="text/plain", status=404)

    contname = f"{COURCEID}-{csid}"
    try:
        cont = client.containers.get(contname)
        return Response(cont.logs(stream=True), mimetype="text/plain")
    except Exception as e:
        return Response(f"Server `{contname}` does not exist.", mimetype="text/plain", status=404)


@app.route("/tests", strict_slashes=False)
def list_tests():
    return Response(test_cases, mimetype="application/json")


@app.route("/tests/<hostport>/<suiteid>/test_<tid>")
def run_test(hostport, suiteid, tid):
    try:
        suite = testsuites[suiteid.lower()]
    except KeyError as e:
        Response(f"{e}", status=404)
    try:
        t = suite(hostport)
    except ValueError as e:
        return Response(f"{e}", status=400)
    test_id = f"test_{tid}"
    try:
        result = t.run_single_test(test_id)
        return Response(jsonify_result(result), mimetype="application/json")
    except Exception as e:
        return Response(f"{e}", status=404)


@app.route("/tests/<hostport>", strict_slashes=False, defaults={"suiteid": ""})
@app.route("/tests/<hostport>/<suiteid>")
def run_tests(hostport, suiteid):
    suiteid = suiteid.lower()
    try:
        t = HTTPTester(hostport)
    except ValueError as e:
        return Response(f"{e}", status=400)
    if suiteid and suiteid not in testsuites:
        return Response(f"Test suite `{suiteid}` not implemented", status=404)
    suites = {suiteid: testsuites[suiteid]} if suiteid else testsuites

    def generate():
        for _, suite in suites.items():
            t = suite(hostport)
            for result in t.run_all_tests():
                yield jsonify_result(result)

    return Response(generate(), mimetype="application/ors")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000")
