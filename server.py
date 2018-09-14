#!/usr/bin/env python3

from flask import Flask, Response
from flask import render_template, abort, request

import os
import re
import requests
import docker
import json
import base64

import tester

app = Flask(__name__)
client = docker.from_env()


def get_student_repo(csid):
    url = "https://raw.githubusercontent.com/phonedude/cs531-f18/master/users/" + csid.strip()
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
    credential = ""
    if os.environ.get("GITHUBKEY"):
        credential = os.environ.get("GITHUBKEY") + "@"
    return "https://{}github.com/{}.git".format(credential, repo)


def jsonify_result(result):
    if result["res"]["payload"]:
        result["res"]["payload"] = base64.b64encode(result["res"]["payload"]).decode("utf-8")
    return json.dumps(result) + "\n"


@app.route("/")
def home():
    show_deployer = True if os.environ.get("GITHUBKEY") else False
    return render_template("index.html", show_deployer=show_deployer)


@app.route("/server/<csid>")
def deploy_server(csid):
    url = get_authorized_repo_url(csid)
    if url is None:
        abort(404)
    imgname = "cs531/" + csid
    contname = "cs531-" + csid
    try:
        print("Building image {}".format(imgname))
        client.images.build(path=url, tag=imgname)
        try:
            print("Removing existing container {}".format(contname))
            cont = client.containers.get(contname)
            cont.remove(force=True)
        except Exception as e:
            print("Container {} does not exist".format(contname))
        print("Running new container {} using {} image".format(contname, imgname))
        deployment_labels = {
            "traefik.backend": csid,
            "traefik.docker.network": "course",
            "traefik.frontend.entryPoints": "http",
            "traefik.frontend.rule": "Host:{}.cs531.cs.odu.edu".format(csid),
            "traefik.port": "80"
        }
        client.containers.run(imgname, detach=True, network="course", labels=deployment_labels, name=contname)
    except Exception as e:
        print(e)
        abort(500)
    return "Service deployed successfully"


@app.route("/tests/<hostport>/test_<int:bucket>_<int:tid>")
def run_test(hostport, bucket, tid):
    tester.update_hostport(hostport)
    test_id = "test_{}_{}".format(bucket, tid)
    try:
        result = tester.run_single_test(test_id)
        return Response(jsonify_result(result), mimetype="application/json")
    except Exception as e:
        abort(404, e)


@app.route("/tests/<hostport>/<int:bucket>")
def run_tests(hostport, bucket):
    bucket = str(bucket)
    if bucket not in tester.test_buckets.keys():
        abort(404, "Test bucket {} not implemented".format(bucket))

    tester.update_hostport(hostport)

    def generate():
        for result in tester.run_bucket_tests(bucket):
            yield jsonify_result(result)

    return Response(generate(), mimetype="application/ors")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000")
