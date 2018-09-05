#!/usr/bin/env python3

from flask import Flask
from flask import render_template, abort, request

import os
import re
import requests
import docker


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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/server", methods=["POST"])
def deploy_server():
    csid = request.form["student"]
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000")
