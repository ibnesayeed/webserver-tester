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


def generate_test_cases_json(test_buckets):
    test_cases = []
    for bucket, tests in test_buckets.items():
        for fname, func in tests.items():
            test_cases.append({"id": fname, "description": func.__doc__, "bucket": bucket})
    return json.dumps(test_cases)

default_tester = HTTPTester()
bucket_numbers = default_tester.test_buckets.keys()
test_cases = generate_test_cases_json(default_tester.test_buckets)


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
    return render_template("index.html", test_buckets=bucket_numbers, test_cases=test_cases, student_ids=student_repos.keys(), show_deployer=DEPLOYER)


@app.route("/servers/<csid>")
def deploy_server(csid):
    repo = get_student_repo(csid.strip())
    repo_url = get_authorized_repo_url(repo)
    if repo_url is None:
        return Response(f"User record '{csid}' not present in https://github.com/{COURSEREPO}/tree/master/users", status=404)

    imgname = "cs531/" + csid
    contname = "cs531-" + csid
    msgs = []

    try:
        print(f"Building image {imgname}")
        client.images.build(path=repo_url, tag=imgname)
        msgs.append(f"Image {imgname} built from the latest code of the {repo} repo.")
    except Exception as e:
        return Response(f"Building image {imgname} from the {repo} repo failed, ensure that the repo is accessible and contains a valid Dockerfile. Response from the Docker daemon: {str(e).replace(CREDENTIALS + '@', '')}", status=500)

    try:
        print(f"Removing existing container {contname}")
        client.containers.get(contname).remove(force=True)
        msgs.append("Related existing container removed.")
    except Exception as e:
        print(f"Container {contname} does not exist")

    try:
        print(f"Running new container {contname} using {imgname} image")
        deployment_labels = {
            "traefik.backend": csid,
            "traefik.docker.network": "course",
            "traefik.frontend.entryPoints": "http",
            "traefik.frontend.rule": f"Host:{csid}.cs531.cs.odu.edu",
            "traefik.port": "80"
        }
        client.containers.run(imgname, detach=True, network="course", labels=deployment_labels, name=contname)
        msgs.append(f"A new container is created and the service {contname} is deployed successfully.")
    except Exception as e:
        return Response(f"Service deployment failed. Response from the Docker daemon: {e}", status=500)

    return Response(" ".join(msgs), status=200)


@app.route("/tests", strict_slashes=False)
def list_tests():
    return Response(test_cases, mimetype="application/json")


@app.route("/tests/<hostport>/test_<int:bucket>_<tid>")
def run_test(hostport, bucket, tid):
    try:
        t = HTTPTester(hostport)
    except ValueError as e:
        return Response(f"{e}", status=400)
    test_id = f"test_{bucket}_{tid}"
    try:
        result = t.run_single_test(test_id)
        return Response(jsonify_result(result), mimetype="application/json")
    except Exception as e:
        return Response(f"{e}", status=404)


@app.route("/tests/<hostport>", strict_slashes=False, defaults={"bucket": ""})
@app.route("/tests/<hostport>/<int:bucket>")
def run_tests(hostport, bucket):
    try:
        t = HTTPTester(hostport)
    except ValueError as e:
        return Response(f"{e}", status=400)
    bucket = str(bucket)
    if bucket and bucket not in t.test_buckets.keys():
        return Response(f"Test bucket {bucket} not implemented", status=404)
    buckets = [bucket] if bucket else t.test_buckets.keys()

    def generate():
        for bucket in buckets:
            for result in t.run_bucket_tests(bucket):
                yield jsonify_result(result)

    return Response(generate(), mimetype="application/ors")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000")
