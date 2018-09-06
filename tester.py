#!/usr/bin/env python3

import subprocess
import time
import os
import sys

host = "localhost"
port = "80"


def make_request(msg_file):
    with open("messages/{}.http".format(msg_file)) as f:
        reqdata = f.read().replace("<SERVERHOST>", "{}:{}".format(host, port))
        tfn = "/tmp/" + str(time.time_ns())
        with open(tfn, "w") as tf:
            tf.write(reqdata)
        output = os.check_output("cat {} | nc -q 1 -w 10 {} {}".format(tfn, host, port), shell=True)
        print(output)
        return output


if __name__ == "__main__":
    print("TODO: A test suite is yet to be implemented")
    if len(sys.argv) > 1:
        hostport = sys.argv[1]
        parts = hostport.split(":")
        host = parts[0]
        if len(parts) > 1:
            port = int(parts[0])
    make_request("server-root")
