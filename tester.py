#!/usr/bin/env python3

import subprocess
import sys
import os
import re
import tempfile
import inspect
import collections
import functools


class HTTPTester():
    """HTTPTester is a special purpose HTTP tester made for CS531 (Web Server Design) course"""

    def __init__(self, hostport="localhost:80"):
        """Initialize an HTTPTester instance for a server specified by the hostport"""

        # Directory where sample HTTP Message files are stored
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "messages")
        # Test function name pattern
        self.TFPATTERN = re.compile("^test_(\d+)_(.+)")

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
            "status_text": "",
            "headers": {},
            "payload": None,
            "payload_size": 0
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
        hdrs = sep = res["payload"] = b""
        m = re.search(b"\r?\n\r?\n", res_bytes)
        if m:
            hdrs = res_bytes[:m.start()]
            sep = res_bytes[slice(*m.span())]
            res["payload"] = res_bytes[m.end():]
        else:
            errors.append("Missing empty line after headers")
        if sep == b"\n\n":
            errors.append("Using LF as header separator instead of CRLF")
        if res["payload"]:
            res["payload_size"] = len(res["payload"])
        hdrs = hdrs.decode("utf-8")
        res["raw_headers"] = hdrs
        hdrs = hdrs.replace("\r", "").replace("\n\t", "\t").replace("\n ", " ")
        lines = hdrs.split("\n")
        status_line = lines.pop(0)
        m = re.match("^([\w\/\.]+)\s+(\d+)\s+(.*)$", status_line)
        if m:
            res["http_version"] = m[1]
            res["status_code"] = int(m[2])
            res["status_text"] = m[3]
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
            @functools.wraps(func)
            def wrapper(self):
                req, res, errors = self.netcat(msg_file)
                try:
                    if not errors:
                        func(self, req, res)
                except AssertionError as e:
                    errors.append("Assertion failed => {}".format(e))
                return {"id": func.__name__, "description": func.__doc__, "errors": errors, "req": req, "res": res}
            return wrapper
        return test_decorator


    @make_request("server-root.http")
    def test_1_healthy_server(self, req, res):
        """Test healthy server root"""
        assert res["status_code"] == 200, "Status expected '200', returned '{}'".format(res["status_code"])
        assert "date" in res["headers"], "Date header should be present"


    @make_request("server-root.http")
    def test_1_text_response(self, req, res):
        """Test server root returns a text response"""
        assert "content-type" in res["headers"], "Content-Type header should be present"
        assert res["headers"]["content-type"].startswith("text/"), "Content-Type should start with 'text/', returned '{}'".format(res["headers"]["content-type"])


    @make_request("server-root.http")
    def test_1_http_version(self, req, res):
        """Test HTTP version"""
        assert res["http_version"] == "HTTP/1.1", "HTTP version expected 'HTTP/1.1', returned '{}'".format(res["http_version"])


    @make_request("server-root.http")
    def test_2_1(self, req, res):
        """Assignment 2, Test 1"""
        assert False, "Placeholder test (not implemented yet!)"


if __name__ == "__main__":
    def print_help():
        print("")
        print("Usage:")
        print("./tester.py [[<host>]:[<port>] [<test-id>|<bucket-numbers>]]")
        print("")
        print("<host>           : Hostname or IP address of the server to be tested (default: 'localhost')")
        print("<port>           : Port number of the server to be tested (default: '80')")
        print("<test-id>        : ID of an individual test function (e.g., 'test_1_healthy_server')")
        print("<bucket-numbers> : Comma separated list of bucket numbers (default: all buckets)")
        print("")

    def colorize(str, code=91):
        return "\033[{}m{}\033[0m".format(code, str)

    if {"-h", "--help"}.intersection(sys.argv):
        print_help()
        sys.exit(0)

    hostport = "localhost:80"
    if len(sys.argv) > 1:
        hostport = sys.argv[1]
    try:
        t = HTTPTester(hostport)
    except ValueError as e:
        print(colorize(e))
        print_help()
        sys.exit(1)
    hostport = "{}:{}".format(t.host, t.port)

    buckets = list(t.test_buckets.keys())
    test_id = None
    if len(sys.argv) > 2:
        if t.TFPATTERN.match(sys.argv[2]):
            test_id = sys.argv[2]
        if re.match("^[\d,]+$", sys.argv[2]):
            buckets = sys.argv[2].split(",")

    def print_result(result):
        print("-" * 79)
        print("{}: {}".format(result["id"], colorize(result["description"], 96)))
        if result["errors"]:
            print(colorize("[FAILED]: {}".format("; ".join(result["errors"]))))
        else:
            print(colorize("[PASSED]", 92))
        print()
        print("> " + result["req"]["raw"].replace("\n", "\n> ")[:-2])
        if result["res"]["raw_headers"]:
            print("< " + result["res"]["raw_headers"].replace("\n", "\n< ")[:-2])
        if result["res"]["payload"]:
            print("< ")
            print("< [Payload redacted ({} bytes)]".format(result["res"]["payload_size"]))
        print()

    def print_summary(hostport, test_results):
        counts = collections.Counter(test_results.values())
        colors = {"PASSED": 92, "FAILED": 91}
        print("=" * 35, "SUMMARY", "=" * 35)
        print("Server: {}".format(colorize(hostport, 96)))
        print("Test Case Results:")
        for t, r in test_results.items():
            print("{}: {}".format(colorize(r, colors[r]), t))
        print("-" * 79)
        print("TOTAL: {}, {}: {}, {}: {}".format(len(test_results), colorize("PASSED", 92), counts["PASSED"], colorize("FAILED", 91), counts["FAILED"]))
        print("=" * 79)

    print("Testing {}".format(hostport))

    try:
        if test_id:
            result = t.run_single_test(test_id)
            print_result(result)
        else:
            test_results = {}
            for bucket in buckets:
                for result in t.run_bucket_tests(bucket):
                    test_results[result["id"]] = "FAILED" if result["errors"] else "PASSED"
                    print_result(result)
            print_summary(hostport, test_results)
    except Exception as e:
        print(colorize(e))
