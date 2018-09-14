#!/usr/bin/env python3

import subprocess
import sys
import os
import re
import tempfile
import inspect
import collections


class Tester():
    """Tester is a special purpose HTTP tester made for CS531 (Web Server Design) course"""

    def __init__(self, hostport="localhost:80"):
        """Initialize a Tester instance for a server specified by the hostport"""

        # Directory where sample HTTP Message files are stored
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "messages")
        # Test function name pattern
        self.TFPATTERN = re.compile("^test_(\d+)_(\d+).*")

        # Identify host and port of the server to be tested
        self.host = "localhost"
        parts = hostport.split(":")
        self.host = parts[0] or "localhost"
        self.port = 80
        if len(parts) > 1 and parts[1]:
            try:
                self.port = int(parts[1])
            except ValueError as e:
                raise ValueError("Invalid port number supplied: '{}'".format(parts[1]))

        # Create buckets of defined test methods
        self.test_buckets = collections.defaultdict(dict)
        for (fname, func) in inspect.getmembers(self, inspect.ismethod):
            m = self.TFPATTERN.match(fname)
            if m:
                self.test_buckets[m[1]][fname] = func


    def netcat(self, msg_file):
        req = {
            "raw": ""
        }
        res = {
            "raw_headers": "",
            "http_version": "",
            "status_code": 0,
            "headers": {},
            "payload": None
        }
        errors = []
        with open(os.path.join(self.MSGDIR, msg_file)) as f:
            req["raw"] = f.read().replace("<SERVERHOST>", "{}:{}".format(self.host, self.port))
        with tempfile.TemporaryFile() as tf:
            tf.write(req["raw"].encode("utf-8"))
            tf.seek(0)
            # TODO: Remove netcat dependency and use pure Python
            # https://stackoverflow.com/questions/8918350/getting-a-raw-unparsed-http-response
            cmd = subprocess.run("nc -w 3 {} {}".format(self.host, self.port), stdin=tf, shell=True, capture_output=True)
        if cmd.returncode == 0:
            pres, errors = self.parse_response(cmd.stdout)
            res = {**res, **pres}
        else:
            errors.append(cmd.stderr.strip().decode("utf-8"))
        return req, res, errors


    def parse_response(self, res_bytes):
        res = {"headers": {}}
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


    def run_single_test(self, test_id):
        err = "Test {} not valid".format(test_id)
        m = self.TFPATTERN.match(test_id)
        if m:
            try:
                return self.test_buckets[m[1]][test_id]()
            except KeyError as e:
                err = "Test {} not implemented".format(test_id)
        raise Exception(err)


    def run_bucket_tests(self, bucket):
        if not self.test_buckets.get(bucket):
            err = "Test bucket {} not implemented".format(bucket)
            raise Exception(err)
        for fname, func in self.test_buckets[bucket].items():
            yield func()


    def make_request(msg_file):
        """Test decorator generator that makes HTTP request using the msg_file.
        Makes the response available for assertions.
        Intended to be used as a decorator from within this class."""

        def test_decorator(func):
            def wrapper(self):
                print("-" * 79)
                print("Running: {}".format(func.__name__))
                print(func.__doc__)
                req, res, errors = self.netcat(msg_file)
                try:
                    if not errors:
                        func(self, req, res)
                        print("\033[92m[PASSED]\033[0m")
                except AssertionError as e:
                    errors.append("Assertion failed => {}".format(e))
                if errors:
                    print("\033[91m[FAILED]\033[0m: {}".format("; ".join(errors)))
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
    def test_1_1(self, req, res):
        """Test healthy server root"""
        assert res["status_code"] == 200, "Status expected '200', returned '{}'".format(res["status_code"])
        assert "date" in res["headers"], "Date header should be present"


    @make_request("server-root.http")
    def test_1_2(self, req, res):
        """Test server root returns a text response"""
        assert "content-type" in res["headers"], "Content-Type header should be present"
        assert res["headers"]["content-type"].startswith("text/"), "Content-Type should start with 'text/', returned '{}'".format(res["headers"]["content-type"])


    @make_request("server-root.http")
    def test_1_3(self, req, res):
        """Test HTTP version"""
        assert res["http_version"] == "HTTP/1.1", "HTTP version expected 'HTTP/1.1', returned '{}'".format(res["http_version"])


    @make_request("server-root.http")
    def test_2_1(self, req, res):
        """Assignment 2, Test 1"""
        assert False, "Placeholder test (not implemented yet!)"


if __name__ == "__main__":
    if {"-h", "--help"}.intersection(sys.argv):
        print("Usage:")
        print("{} [[<host>]:[<port>] [<test-id>|<bucket-numbers>]]".format(sys.argv[0]))
        print()
        print("<host>           : Hostname or IP address of the server to be tested (default: localhost)")
        print("<port>           : Port number of the server to be tested (default: 80)")
        print("<test-id>        : Name of an individual test function (e.g., test_1_1)")
        print("<bucket-numbers> : Comma separated list of bucket numbers (default: all buckets)")
        print()
        sys.exit(0)

    hostport = "localhost:80"
    if len(sys.argv) > 1:
        hostport = sys.argv[1]
    try:
        t = Tester(hostport)
    except ValueError as e:
        print(e)
        sys.exit(1)

    buckets = list(t.test_buckets.keys())
    test_id = None

    if len(sys.argv) > 2:
        if t.TFPATTERN.match(sys.argv[2]):
            test_id = sys.argv[2]
        if re.match("^[\d,]+$", sys.argv[2]):
            buckets = sys.argv[2].split(",")

    print("Testing {}:{}".format(t.host, t.port))

    try:
        if test_id:
            t.run_single_test(test_id)
        else:
            passed_count = failed_count = 0
            for bucket in buckets:
                for result in t.run_bucket_tests(bucket):
                    if result["errors"]:
                        failed_count += 1
                    else:
                        passed_count += 1
            print("=" * 35, "SUMMARY", "=" * 35)
            print("Server => {}:{}".format(t.host, t.port))
            print("\033[92mPASSED\033[0m =>", passed_count)
            print("\033[91mFAILED\033[0m =>", failed_count)
            print("=" * 79)
    except Exception as e:
        print(e)
