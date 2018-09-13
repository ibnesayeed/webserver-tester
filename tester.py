#!/usr/bin/env python3

import subprocess
import sys
import os
import re
import tempfile
import inspect
import collections

host = "localhost"
port = "80"
passed_count = failed_count = 0

MSGDIR = os.path.join(os.path.dirname(__file__), "messages")

tfunc_pattern = re.compile("^test_(\d+)_(\d+).*")
test_buckets = collections.defaultdict(dict)


def make_test_buckets():
    for (fname, func) in inspect.getmembers(sys.modules[__name__], inspect.isfunction):
        m = tfunc_pattern.match(fname)
        if m:
            test_buckets[m[1]][fname] = func


def run_single_test(test_id):
    err = "Test {} not valid".format(test_id)
    m = tfunc_pattern.match(test_id)
    if m:
        try:
            return test_buckets[m[1]][test_id]()
        except KeyError as e:
            err = "Test {} not implemented".format(test_id)
            print(err)
    raise Exception(err)


def run_bucket_tests(bucket):
    if not test_buckets.get(bucket):
        err = "Test bucket {} not implemented".format(bucket)
        print(err)
        raise Exception(err)
    for fname, func in test_buckets[bucket].items():
        yield func()


def netcat(msg_file):
    req = {
        "raw": ""
    }
    res = {}
    errors = []
    with open(os.path.join(MSGDIR, msg_file)) as f:
        req["raw"] = f.read().replace("<SERVERHOST>", "{}:{}".format(host, port))
    with tempfile.TemporaryFile() as tf:
        tf.write(req["raw"].encode("utf-8"))
        tf.seek(0)
        cmd = subprocess.run("nc -w 3 {} {}".format(host, port), stdin=tf, shell=True, capture_output=True)
    if cmd.returncode == 0:
        res, errors = parse_response(cmd.stdout)
    return req, res, errors


def parse_response(res_bytes):
    res = {
        "raw_headers": "",
        "http_version": "",
        "status_code": 0,
        "headers": {},
        "payload": None
    }
    errors = []
    if not res_bytes.strip():
        errors.append("Empty response")
        return res, errors
    hdrs, sep, res["payload"] = res_bytes.partition(b"\r\n\r\n")
    if not sep:
        errors.append("Missing empty line after headers")
    hdrs = hdrs.decode("utf-8")
    res["raw_headers"] = hdrs
    hdrs = hdrs.replace("\r", "").replace("\n\t", "\t").replace("\n ", " ")
    lines = hdrs.split("\n")
    status_line = lines.pop(0)
    m = re.match("^([\w\/\.]+)\s+(\d+)\s.*", status_line)
    if m:
        res["http_version"] = m[1]
        res["status_code"] = int(m[2])
    for line in lines:
        kv = line.split(":", 1)
        if len(kv) < 2:
            errors.append("Malformed header line => {}".format(line))
        else:
            res["headers"][kv[0].lower()] = kv[1].strip()
    return res, errors


def make_request(msg_file):
    def test_decorator(func):
        def wrapper():
            global passed_count, failed_count
            print("=" * 79)
            print("Running: {}".format(func.__name__))
            print(func.__doc__)
            req, res, errors = netcat(msg_file)
            try:
                if errors:
                    print("\n".join(errors))
                    raise AssertionError("Malformed response")
                func(req, res)
                passed_count += 1
                print("\033[92m[PASSED]\033[0m")
            except AssertionError as e:
                failed_count += 1
                errors.append("Assertion failed: {}".format(e))
                print(": ".join(filter(None, ["\033[91m[FAILED]\033[0m", str(e)])))
            print()
            print(req["raw"])
            print(res["raw_headers"])
            if res["payload"]:
                print()
                print("[Payload redacted ({} bytes)]".format(len(res["payload"])))
            print()
            return {"id": func.__name__, "description": func.__doc__, "errors": errors, "req": req, "res": res}
        return wrapper
    return test_decorator


@make_request("server-root.http")
def test_1_1(req, res):
    """Server root is healthy"""
    assert res["status_code"] == 200, "Retunrs 200"
    assert "date" in res["headers"], "Date header is present"


@make_request("server-root.http")
def test_1_2(req, res):
    """Server root returns a text response"""
    assert "content-type" in res["headers"], "Content-Type header is present"
    assert res["headers"]["content-type"].startswith("text/"), "Content-Type starts with text/"


@make_request("server-root.http")
def test_1_3(req, res):
    """HTTP version is 1.1"""
    assert res["http_version"] == "HTTP/1.1", "HTTP version is exactly HTTP/1.1"


@make_request("server-root.http")
def test_2_1(req, res):
    """Assignment 2, Test 1"""
    assert False, "Placeholder test (not implemented yet!)"


make_test_buckets()


if __name__ == "__main__":
    buckets = list(test_buckets.keys())
    test_id = None

    if {"-h", "--help"}.intersection(sys.argv):
        print("Usage:")
        print("{} [[<host>]:[<port>] [<test-id>|<bucket-numbers>]]".format(sys.argv[0]))
        print()
        print("<host>           : Hostname or IP address of the server to be tested (default: localhost)")
        print("<port>           : Port number of the server to be tested (default: 80)")
        print("<test-id>        : Name of an individual test function (e.g., test_1_1)")
        print("<bucket-numbers> : Comma separated list of bucket numbers (default: {})".format(",".join(buckets)))
        print()
        sys.exit(0)

    if len(sys.argv) > 1:
        parts = sys.argv[1].split(":")
        if parts[0]:
            host = parts[0]
        if len(parts) > 1 and parts[1]:
            port = int(parts[0])

    if len(sys.argv) > 2:
        if tfunc_pattern.match(sys.argv[2]):
            test_id = sys.argv[2]
        if re.match("^[\d,]+$", sys.argv[2]):
            buckets = sys.argv[2].split(",")

    print("Testing {}:{}".format(host, port))

    if test_id:
        run_single_test(test_id)
    else:
        for bucket in buckets:
            for _ in run_bucket_tests(bucket): pass

    print("#" * 35, "SUMMARY", "#" * 35)
    print("Server => {}:{}".format(host, port))
    print("\033[92mPASSED\033[0m =>", passed_count)
    print("\033[91mFAILED\033[0m =>", failed_count)
    print("#" * 79)
