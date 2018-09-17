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
COURSEREPO = os.environ.get("COURSEREPO") or "phonedude/cs531-f18"
# This is needed if student repos are kept private (ideally, supply it via the environment variable)
CREDENTIALS = os.environ.get("GITHUBKEY") or ""

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


def get_student_repo(csid):
    url = "https://raw.githubusercontent.com/{}/master/users/{}".format(COURSEREPO, csid.strip())
    req = requests.get(url)
    if req.status_code == 200:
        repo = req.text.strip().rstrip('.git')
        match = re.search("github.com[:/]([^/]+)/([^/]+)", repo)
        if match is not None:
            return "{}/{}".format(match[1], match[2])
    return None


def get_authorized_repo_url(csid):
    repo = get_student_repo(csid)
    if repo is None:
        return None
    cred = CREDENTIALS + "@" if CREDENTIALS else ""
    return "https://{}github.com/{}.git".format(cred, repo)


def jsonify_result(result):
    result["res"]["payload"] = base64.b64encode(result["res"]["payload"]).decode("utf-8") if result["res"]["payload"] else ''
    return json.dumps(result) + "\n"


@app.route("/")
def home():
    return render_template("index.html", test_buckets=bucket_numbers, test_cases=test_cases, show_deployer=DEPLOYER)


@app.route("/servers/<csid>")
def deploy_server(csid):
    url = get_authorized_repo_url(csid)
    if url is None:
        return Response("User record '{}' not present in https://github.com/{}/tree/master/users".format(csid, COURSEREPO), status=404)

    repo = get_student_repo(csid)
    imgname = "cs531/" + csid
    contname = "cs531-" + csid
    msgs = []

    try:
        print("Building image {}".format(imgname))
        client.images.build(path=url, tag=imgname)
        msgs.append("Image {} built from the latest code of the {} repo.".format(imgname, repo))
    except Exception as e:
        return Response("Building image {} from the {} repo failed, ensure that the repo is accessible and contains a valid Dockerfile. Response from the Docker daemon: {}".format(imgname, repo, e), status=500)

    try:
        print("Removing existing container {}".format(contname))
        client.containers.get(contname).remove(force=True)
        msgs.append("Related existing container removed.")
    except Exception as e:
        print("Container {} does not exist".format(contname))

    try:
        print("Running new container {} using {} image".format(contname, imgname))
        deployment_labels = {
            "traefik.backend": csid,
            "traefik.docker.network": "course",
            "traefik.frontend.entryPoints": "http",
            "traefik.frontend.rule": "Host:{}.cs531.cs.odu.edu".format(csid),
            "traefik.port": "80"
        }
        client.containers.run(imgname, detach=True, network="course", labels=deployment_labels, name=contname)
        msgs.append("A new container is created and the service {} is deployed successfully.".format(contname))
    except Exception as e:
        return Response("Service deployment failed. Response from the Docker daemon: {}".format(e), status=500)

    return Response(" ".join(msgs), status=200)


@app.route("/tests", strict_slashes=False)
def list_tests():
    return Response(test_cases, mimetype="application/json")


@app.route("/tests/<hostport>/test_<int:bucket>_<tid>")
def run_test(hostport, bucket, tid):
    try:
        t = HTTPTester(hostport)
    except ValueError as e:
        return Response("{}".format(e), status=400)
    test_id = "test_{}_{}".format(bucket, tid)
    try:
        result = t.run_single_test(test_id)
        return Response(jsonify_result(result), mimetype="application/json")
    except Exception as e:
        return Response("{}".format(e), status=404)


@app.route("/tests/<hostport>", strict_slashes=False, defaults={"bucket": None})
@app.route("/tests/<hostport>/<int:bucket>")
def run_tests(hostport, bucket):
    try:
        t = HTTPTester(hostport)
    except ValueError as e:
        return Response("{}".format(e), status=400)
    if bucket and str(bucket) not in t.test_buckets.keys():
        return Response("Test bucket {} not implemented".format(bucket), status=404)
    buckets = [str(bucket)] if bucket else t.test_buckets.keys()

    def generate():
        for bucket in buckets:
            for result in t.run_bucket_tests(bucket):
                yield jsonify_result(result)

    return Response(generate(), mimetype="application/ors")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000")
