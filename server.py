#!/usr/bin/env python3

from flask import Flask
from flask import render_template, abort

import os
import requests

app = Flask(__name__)


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
    return "https://{}github.com/{}".format(credential, repo)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/server", methods=["POST"])
def deploy_server():
    csid = request.form["student"]
    url = get_authorized_repo_url(csid)
    if url is None:
        abort(404)
    print("TODO: Deploying from {}".format(url))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000", debug=True)
