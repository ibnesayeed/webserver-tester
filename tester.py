#!/usr/bin/env python3

import sys
import os
import re
import inspect
import collections
import functools
import socket


class HTTPTester():
    """HTTPTester is a special purpose HTTP tester made for CS531 (Web Server Design) course"""

    def __init__(self, hostport="localhost:80"):
        """Initialize an HTTPTester instance for a server specified by the hostport"""

        # Directory where sample HTTP Message files are stored
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "messages")
        # Test function name pattern
        self.TFPATTERN = re.compile("^test_(\d+)_(.+)")

        # Socket timeouts
        self.CONNECTION_TIMEOUT = 0.2
        self.SEND_DATA_TIMEOUT = 3.0
        self.RECV_FIRST_BYTE_TIMEOUT = 1.0
        self.RECV_END_TIMEOUT = 0.05

        # Identify host and port of the server to be tested
        self.host = "localhost"
        parts = hostport.split(":")
        self.host = parts[0] or "localhost"
        self.port = 80
        if len(parts) > 1 and parts[1]:
            try:
                self.port = int(parts[1])
            except ValueError as e:
                raise ValueError(f"Invalid port number supplied: '{parts[1]}'")
        self.hostport = self.host if self.port == 80 else f"{self.host}:{self.port}"

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
            "payload_size": 0,
            "connection": "closed"
        }
        errors = []
        with open(os.path.join(self.MSGDIR, msg_file), "rb") as f:
            msg = self.replace_placeholders(f.read())
            hdrs, sep, pld = self.split_http_message(msg)
            msg = hdrs.replace(b"\r", b"").replace(b"\n", b"\r\n") + b"\r\n\r\n" + pld
            req["raw"] = msg.decode()
            sock = socket.socket()
            try:
                sock.settimeout(self.CONNECTION_TIMEOUT)
                sock.connect((self.host, self.port))
            except Exception as e:
                errors.append(f"Connection to the server '{self.host}:{self.port}' failed: {e}")
                return req, res, errors
            try:
                sock.settimeout(self.SEND_DATA_TIMEOUT)
                sock.sendall(msg)
            except Exception as e:
                errors.append(f"Sending data failed: {e}")
                return req, res, errors
            try:
                data = []
                sock.settimeout(self.RECV_FIRST_BYTE_TIMEOUT)
                buf = sock.recv(4096)
                sock.settimeout(self.RECV_END_TIMEOUT)
                while buf:
                    data.append(buf)
                    buf = sock.recv(4096)
            except socket.timeout as e:
                res["connection"] = "alive"
            except Exception as e:
                errors.append(f"Communication failed: {e}")
            pres, errors = self.parse_response(b"".join(data))
            res = {**res, **pres}
        return req, res, errors


    def replace_placeholders(self, msg):
        replacements = {
            "<HOST>": self.host,
            "<PORT>": str(self.port),
            "<HOSTPORT>": self.hostport
        }
        for placeholder, replacement in replacements.items():
            msg = msg.replace(placeholder.encode(), replacement.encode())
        return msg


    def split_http_message(self, msg):
        m = re.search(b"\r?\n\r?\n", msg)
        if m:
            return msg[:m.start()], msg[slice(*m.span())], msg[m.end():]
        else:
            return msg, b"", b""


    def parse_response(self, msg):
        res = {"headers": {}}
        errors = []
        if not msg.strip():
            errors.append("Empty response")
            return res, errors
        hdrs, sep, res["payload"] = self.split_http_message(msg)
        if not sep:
            errors.append("Missing empty line after headers")
        if sep == b"\n\n":
            errors.append("Using LF as header separator instead of CRLF")
        if res["payload"]:
            res["payload_size"] = len(res["payload"])
        hdrs = hdrs.decode()
        res["raw_headers"] = hdrs
        hdrs = hdrs.replace("\r", "").replace("\n\t", "\t").replace("\n ", " ")
        lines = hdrs.split("\n")
        status_line = lines.pop(0)
        m = re.match("^([\w\/\.]+)\s+(\d+)\s+(.*)$", status_line)
        if m:
            res["http_version"] = m[1]
            res["status_code"] = int(m[2])
            res["status_text"] = m[3]
        else:
            errors.append(f"Malformed status line: {status_line}")
        for line in lines:
            kv = line.split(":", 1)
            if len(kv) < 2:
                errors.append(f"Malformed header line: {line}")
            else:
                res["headers"][kv[0].lower()] = kv[1].strip()
        return res, errors


    def run_single_test(self, test_id):
        err = f"Test {test_id} not valid"
        m = self.TFPATTERN.match(test_id)
        if m:
            try:
                return self.test_buckets[m[1]][test_id]()
            except KeyError as e:
                err = f"Test {test_id} not implemented"
        raise Exception(err)


    def run_bucket_tests(self, bucket):
        if not self.test_buckets.get(bucket):
            err = f"Test bucket {bucket} not implemented"
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
                    errors.append(f"ASSERTION: {e}")
                return {"id": func.__name__, "description": func.__doc__, "errors": errors, "req": req, "res": res}
            return wrapper
        return test_decorator


############################### BEGIN TEST CASES ###############################


    @make_request("server-root.http")
    def test_1_healthy_server(self, req, res):
        """Test healthy server root"""
        assert res["status_code"] == 200, f"Status expected '200', returned '{res['status_code']}'"
        assert "date" in res["headers"], "Date header should be present"


    @make_request("server-root.http")
    def test_1_text_response(self, req, res):
        """Test server root returns a text response"""
        assert "content-type" in res["headers"], "Content-Type header should be present"
        assert res["headers"]["content-type"].startswith("text/"), f"Content-Type should start with 'text/', returned '{res['headers']['content-type']}'"


    @make_request("server-root.http")
    def test_1_http_version(self, req, res):
        """Test HTTP version"""
        assert res["http_version"] == "HTTP/1.1", f"HTTP version expected 'HTTP/1.1', returned '{res['http_version']}'"


    @make_request("malformed-header.http")
    def test_1_bad_request_header(self, req, res):
        """Test whether the server recognizes malformed headers"""
        assert res["status_code"] == 400, f"Status expected '400', returned '{res['status_code']}'"


    @make_request("server-root.http")
    def test_2_1(self, req, res):
        """Assignment 2, Test 1"""
        assert False, "Placeholder test (not implemented yet!)"


################################ END TEST CASES ################################


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
        return f"\033[{code}m{str}\033[0m"

    if {"-h", "--help"}.intersection(sys.argv):
        print_help()
        sys.exit(0)

    if len(sys.argv) < 2:
        print()
        print("Following test cases are available:")
        print()
        for bucket, tests in HTTPTester().test_buckets.items():
            for fname, func in tests.items():
                print(f"[Bucket {bucket}] {colorize(fname)}: {colorize(func.__doc__, 96)}")
        print()
        print(f"For help run: {colorize('./tester.py -h')}")
        print()
        sys.exit(0)

    try:
        t = HTTPTester(sys.argv[1])
    except ValueError as e:
        print(colorize(e))
        print_help()
        sys.exit(1)
    hostport = f"{t.host}:{t.port}"

    buckets = list(t.test_buckets.keys())
    test_id = None
    if len(sys.argv) > 2:
        if t.TFPATTERN.match(sys.argv[2]):
            test_id = sys.argv[2]
        if re.match("^[\d,]+$", sys.argv[2]):
            buckets = sys.argv[2].split(",")

    def print_result(result):
        print("-" * 79)
        print(f"{result['id']}: {colorize(result['description'], 96)}")
        if result["errors"]:
            for err in result["errors"]:
                print(colorize(f"[FAILED] {err}"))
        else:
            print(colorize("[PASSED]", 92))
        print()
        print("> " + result["req"]["raw"].replace("\n", "\n> ")[:-2])
        if result["res"]["raw_headers"]:
            print("< " + result["res"]["raw_headers"].replace("\n", "\n< ")[:-2])
        if result["res"]["payload"]:
            print("< ")
            print(f"< [Payload redacted ({result['res']['payload_size']} bytes)]")
        print()

    def print_summary(hostport, test_results):
        counts = collections.Counter(test_results.values())
        colors = {"PASSED": 92, "FAILED": 91}
        print("=" * 35, "SUMMARY", "=" * 35)
        print(f"Server: {colorize(hostport, 96)}")
        print("Test Case Results:")
        for test, result in test_results.items():
            print(f"{colorize(result, colors[result])}: {test}")
        print("-" * 79)
        print(f"TOTAL: {len(test_results)}, {colorize('PASSED', 92)}: {counts['PASSED']}, {colorize('FAILED', 91)}: {counts['FAILED']}")
        print("=" * 79)

    print(f"Testing {hostport}")

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
