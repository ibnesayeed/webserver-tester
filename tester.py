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
        self.RECV_END_TIMEOUT = 0.5

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

        # Create reusable socket reference
        self.sock = None

        # Create batches of test methods in their defined order
        self.test_batches = collections.defaultdict(dict)
        tfuncs = [f for f in inspect.getmembers(self, inspect.ismethod) if self.TFPATTERN.match(f[0])]
        for tf in tfuncs:
            tf[1].__func__.__orig_lineno__ = tf[1].__wrapped__.__code__.co_firstlineno if hasattr(tf[1], "__wrapped__") else tf[1].__code__.co_firstlineno
        for (fname, func) in sorted(tfuncs, key=lambda x: x[1].__orig_lineno__):
            m = self.TFPATTERN.match(fname)
            self.test_batches[m[1]][fname] = func


    def connect_sock(self):
        if not self.sock:
            self.sock = socket.socket()
            self.sock.settimeout(self.CONNECTION_TIMEOUT)
            self.sock.connect((self.host, self.port))


    def reset_sock(self):
        self.sock.close()
        self.sock = None


    def netcat(self, msg_file, keep_alive=False, **kwargs):
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
            msg = self.replace_placeholders(f.read(), **kwargs)
            hdrs, sep, pld = self.split_http_message(msg)
            msg = hdrs.replace(b"<PIPELINE>", b"").replace(b"\r", b"").replace(b"\n", b"\r\n") + b"\r\n\r\n" + pld
            req["raw"] = msg.decode()
            try:
                self.connect_sock()
            except Exception as e:
                errors.append(f"Connection to the server '{self.host}:{self.port}' failed: {e}")
                self.reset_sock()
                return req, res, errors
            try:
                self.sock.settimeout(self.SEND_DATA_TIMEOUT)
                self.sock.sendall(msg)
            except Exception as e:
                errors.append(f"Sending data failed: {e}")
                keep_alive or self.reset_sock()
                return req, res, errors
            try:
                data = []
                self.sock.settimeout(self.RECV_FIRST_BYTE_TIMEOUT)
                buf = self.sock.recv(4096)
                self.sock.settimeout(self.RECV_END_TIMEOUT)
                while buf:
                    data.append(buf)
                    buf = self.sock.recv(4096)
            except socket.timeout as e:
                res["connection"] = "alive"
            except Exception as e:
                errors.append(f"Reading data failed: {e}")
            keep_alive or self.reset_sock()
            pres, errors = self.parse_response(b"".join(data))
            res = {**res, **pres}
        return req, res, errors


    def replace_placeholders(self, msg, **kwargs):
        replacements = {
            "<HOST>": self.host,
            "<PORT>": str(self.port),
            "<HOSTPORT>": self.hostport
        }
        for k, v in kwargs.items():
            replacements[f"<{k}>"] = v

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
            errors.append("Using `LF` as header separator instead of `CRLF`")
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
            errors.append(f"Malformed status line `{status_line}`")
        for line in lines:
            kv = line.split(":", 1)
            if len(kv) < 2:
                errors.append(f"Malformed header line `{line}`")
            else:
                k = kv[0].strip()
                if k != kv[0]:
                    errors.append(f"Header name `{kv[0]}` has spurious white-spaces")
                res["headers"][k.lower()] = kv[1].strip()
        return res, errors


    def run_single_test(self, test_id):
        err = f"Test {test_id} not valid"
        m = self.TFPATTERN.match(test_id)
        if m:
            try:
                return self.test_batches[m[1]][test_id]()
            except KeyError as e:
                err = f"Test {test_id} not implemented"
        raise Exception(err)


    def run_batch_tests(self, batch):
        if not self.test_batches.get(batch):
            err = f"Assignment {batch} not implemented"
            raise Exception(err)
        for fname, func in self.test_batches[batch].items():
            yield func()


    def make_request(msg_file, **kwargs):
        """Test decorator generator that makes HTTP request using the msg_file.
        Makes the response available for assertions.
        Intended to be used as a decorator from within this class."""

        def test_decorator(func):
            @functools.wraps(func)
            def wrapper(self):
                req, res, errors = self.netcat(msg_file, **kwargs)
                overwrite = None
                try:
                    if not errors:
                        overwrite = func(self, req, res)
                except AssertionError as e:
                    errors.append(f"ASSERTION: {e}")
                if overwrite:
                    req = overwrite["req"]
                    res = overwrite["res"]
                    errors = overwrite["errors"]
                return {"id": func.__name__, "description": func.__doc__, "errors": errors, "req": req, "res": res}
            return wrapper
        return test_decorator


############################### ASSERTION HELPERS ##############################


    def check_status_is(self, res, status):
        sc = res["status_code"]
        assert status == sc, f"Status expected `{status}`, returned `{sc}`"


    def check_version_is(self, res, version):
        ver = res["http_version"]
        assert version == ver, f"HTTP version expected `{status}`, returned `{ver}`"


    def check_header_present(self, res, header):
        assert header.lower() in res["headers"], f"`{header}` header should be present"


    def check_header_is(self, res, header, value):
        check_header_present(res, header)
        val = res["headers"].get(header, "")
        assert value == val, f"`{header}` header should be `{value}`, returned `{val}`"


    def check_header_contains(self, res, header, value):
        check_header_present(res, header)
        val = res["headers"].get(header, "")
        assert value in val, f"`{header}` header should contain `{value}`, returned `{val}`"


    def check_header_begins(self, res, header, value):
        check_header_present(res, header)
        val = res["headers"].get(header, "")
        assert val.startswith(value), f"`{header}` header should begin with `{value}`, returned `{val}`"


    def check_header_ends(self, res, header, value):
        check_header_present(res, header)
        val = res["headers"].get(header, "")
        assert val.endswith(value), f"`{header}` header should end with `{value}`, returned `{val}`"


    def check_date_valid(self, res):
        check_header_present(res, "Date")
        datehdr = res["headers"].get("date", "")
        assert re.match("(Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} \d{2}:\d{2}:\d{2} GMT", datehdr), f"`Date: {datehdr}` is not in the preferred format as per `RCF7231 (section-7.1.1.1)`"


    def check_etag_valid(self, res):
        check_header_present(res, "ETag")
        datehdr = res["headers"].get("etag", "")
        etag = res["headers"].get("etag", "")
        assert etag.strip('"'), "`ETag` should not be empty"
        assert etag.strip('"') != etag, f'`ETag` should be in double quotes like `"{etag}"`, returned `{etag}`'


    def check_redirects_to(self, res, status, location):
        check_status_is(res, status)
        check_header_ends(res, "Location", location)


    def check_payload_empty(self, res):
        assert not res["payload"], f"Payload expected empty, returned `{res['payload_size']}` bytes"


    def check_payload_not_empty(self, res):
        assert res["payload"], "Payload expected non-empty, returned empty"


    def check_payload_size(self, res, value):
        val = res["payload_size"]
        assert value == val, f"Payload size expected `{value}` bytes, returned `{val}`"


    def check_payload_is(self, res, value):
        check_payload_not_empty(res)
        assert value.encode() == res["payload"], f"Payload should exactly be `{value}`"


    def check_payload_contains(self, res, value):
        check_payload_not_empty(res)
        assert value.encode() in res["payload"], f"Payload should contain `{value}`"


    def check_payload_begins(self, res, value):
        check_payload_not_empty(res)
        assert res["payload"].startswith(value.encode()), f"Payload should begin with `{value}`"


    def check_payload_ends(self, res, value):
        check_payload_not_empty(res)
        assert res["payload"].endswith(value.encode()), f"Payload should end with `{value}`"


    def check_connection_alive(self, res, explicit=False):
        reason = "explicit `Connection: keep-alive` header" if explicit else "no explicit `Connection: close` header"
        assert res["connection"] == "alive", "Socket connection should be kept alive due to {reason}"


    def check_connection_closed(self, res):
        assert res["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"


############################### BEGIN TEST CASES ###############################


    @make_request("get-root.http")
    def test_0_healthy_server(self, req, res):
        """Test healthy server root"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        assert "date" in res["headers"], "`Date` header should be present"
        datehdr = res["headers"].get("date", "")
        assert re.match("(Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} \d{2}:\d{2}:\d{2} GMT", datehdr), f"`Date: {datehdr}` is not in the preferred format as per `RCF7231 (section-7.1.1.1)`"
        assert "content-type" in res["headers"], "`Content-Type` header should be present"
        assert res["http_version"] == "HTTP/1.1", f"HTTP version expected `HTTP/1.1`, returned `{res['http_version']}`"


    @make_request("malformed-header.http")
    def test_0_bad_request_header(self, req, res):
        """Test whether the server recognizes malformed headers"""
        assert res["status_code"] == 400, f"Status expected `400`, returned `{res['status_code']}`"


    @make_request("get-url.http", PATH="/a1-test/2/index.html")
    def test_1_url_get_ok(self, req, res):
        """Test whether the URL of the assignment 1 directory returns HTTP/1.1 200 OK on GET"""
        assert res["http_version"] == "HTTP/1.1", f"HTTP version expected `HTTP/1.1`, returned `{res['http_version']}`"
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"


    @make_request("method-url.http", METHOD="HEAD", PATH="/a1-test/2/index.html")
    def test_1_url_head_ok(self, req, res):
        """Test whether the URL of the assignment 1 directory returns 200 on HEAD"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("method-path.http", METHOD="HEAD", PATH="/a1-test/2/index.html")
    def test_1_path_head_ok(self, req, res):
        """Test whether the relative path of the assignment 1 directory returns 200 on HEAD"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("method-path.http", METHOD="OPTIONS", PATH="/a1-test/2/index.html")
    def test_1_path_options_ok(self, req, res):
        """Test whether the relative path of the assignment 1 directory returns 200 on OPTIONS"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        assert "allow" in res["headers"], "`Allow` header should be present"


    @make_request("get-path.http", PATH="/1/1.1/go%20hokies.html")
    def test_1_get_missing(self, req, res):
        """Test whether a non-existing path returns 404 on GET"""
        assert res["http_version"] == "HTTP/1.1", f"HTTP version expected `HTTP/1.1`, returned `{res['http_version']}`"
        assert res["status_code"] == 404, f"Status expected `404`, returned `{res['status_code']}`"


    @make_request("get-path.http", PATH="/a1-test/a1-test/")
    def test_1_get_duplicate_path_prefix(self, req, res):
        """Test tight path prefix checking"""
        assert res["http_version"] == "HTTP/1.1", f"HTTP version expected `HTTP/1.1`, returned `{res['http_version']}`"
        assert res["status_code"] == 404, f"Status expected `404`, returned `{res['status_code']}`"


    @make_request("unsupported-version.http", VERSION="HTTP/2.3")
    def test_1_unsupported_version(self, req, res):
        """Test whether a request with unsupported version returns 505"""
        assert res["status_code"] == 505, f"Status expected `505`, returned `{res['status_code']}`"


    @make_request("unsupported-version.http", VERSION="HTTP/1.11")
    def test_1_tight_unsupported_version_check(self, req, res):
        """Test tight HTTP version checking to not match HTTP/1.11"""
        assert res["status_code"] == 505, f"Status expected `505`, returned `{res['status_code']}`"


    @make_request("invalid-request.http")
    def test_1_invalid_request(self, req, res):
        """Test whether an invalid request returns 400"""
        assert res["status_code"] == 400, f"Status expected `400`, returned `{res['status_code']}`"


    @make_request("missing-host.http")
    def test_1_missing_host_header(self, req, res):
        """Test whether missing Host header in a request returns 400"""
        assert res["status_code"] == 400, f"Status expected `400`, returned `{res['status_code']}`"


    @make_request("method-path.http", METHOD="POST", PATH="/a1-test/")
    def test_1_post_not_implemented(self, req, res):
        """Test whether the assignment 1 returns 501 on POST"""
        assert res["status_code"] == 501, f"Status expected `501`, returned `{res['status_code']}`"


    @make_request("method-path.http", METHOD="TRACE", PATH="/a1-test/1/1.4/")
    def test_1_trace_echoback(self, req, res):
        """Test whether the server echoes back the request on TRACE"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("message/http"), f"`Content-Type` should start with `message/http`, returned `{ctype}`"
        assert res["payload"] and res["payload"].startswith(b"TRACE /a1-test/1/1.4/ HTTP/1.1"), f"Payload should start with `TRACE /a1-test/1/1.4/ HTTP/1.1`"


    @make_request("get-url.http", PATH="/a1-test/1/1.4/test%3A.html")
    def test_1_get_escaped_file_name(self, req, res):
        """Test whether the escaped file name is respected"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        assert res["payload"] and b"lower case html" in res["payload"], "Payload should contain `lower case html`"


    @make_request("get-url.http", PATH="/a1-test/1/1.4/escape%25this.html")
    def test_1_get_escape_escaping_character(self, req, res):
        """Test whether the escaped escaping caracter in a file name is respected"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        assert res["payload"] and b"Go Monarchs!" in res["payload"], "Payload should contain `Go Monarchs!`"


    @make_request("get-url.http", PATH="/a1-test/2/0.jpeg")
    def test_1_get_jpeg_image(self, req, res):
        """Test whether a JPEG image returns 200 with proper Content-Length on GET"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        clength = res["headers"].get("content-length", "[ABSENT]")
        assert clength == "38457", f"`Content-Length` expected `38457`, returned `{clength}`"
        assert res["payload"] and res["payload_size"] == 38457, f"Payload length expected `38457` bytes, returned `{res['payload_size']}`"


    @make_request("get-url.http", PATH="/a1-test/2/0.JPEG")
    def test_1_get_case_sensitive_file_extension(self, req, res):
        """Test whether file extensions are treated case-sensitive"""
        assert res["http_version"] == "HTTP/1.1", f"HTTP version expected `HTTP/1.1`, returned `{res['http_version']}`"
        assert res["status_code"] == 404, f"Status expected `404`, returned `{res['status_code']}`"


    @make_request("get-url.http", PATH="/a1-test/4/thisfileisempty.txt")
    def test_1_get_empty_text_file(self, req, res):
        """Test whether an empty file returns zero bytes with 200 on GET"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/plain"), f"`Content-Type` should start with `text/plain`, returned `{ctype}`"
        clength = res["headers"].get("content-length", "[ABSENT]")
        assert clength == "0", f"`Content-Length` expected `0`, returned `{clength}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("get-url.http", PATH="/a1-test/4/directory3isempty")
    def test_1_get_empty_directory(self, req, res):
        """Test whether an empty directory returns zero bytes and a valid Content-Type with 200 on GET"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("application/octet-stream"), f"`Content-Type` should start with `application/octet-stream`, returned `{ctype}`"
        clength = res["headers"].get("content-length", "[ABSENT]")
        assert clength == "0", f"`Content-Length` expected `0`, returned `{clength}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("get-url.http", PATH="/a1-test/1/1.2/arXiv.org.Idenitfy.repsonse.xml")
    def test_1_get_filename_with_many_dots(self, req, res):
        """Test whether file names with multiple dots return 200 on GET"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/xml"), f"`Content-Type` should start with `text/xml`, returned `{ctype}`"


    @make_request("get-url.http", PATH="/a1-test/2/6.gif")
    def test_1_get_magic_cookie_of_a_binary_file(self, req, res):
        """Test whether a GIF file contains identifying magic cookie"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        assert res["payload"] and res["payload"].startswith(b"GIF89a"), f"Payload should contain `GIF89a` magic cookie for GIF"


    @make_request("get-url.http", PATH="/a2-test/")
    def test_2_get_directory_listing(self, req, res):
        """Test whether a2-test directory root returns directory listing"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert res["payload"] and b"coolcar.html" in res["payload"] and b"ford" in res["payload"], "Payload should contain all file and folder names immediately under `/a2-test/` directory"
        assert res["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"


    @make_request("get-url.http", PATH="/a2-test/2")
    def test_2_redirect_to_trailing_slash_for_directory_url(self, req, res):
        """Test whether redirects URL to trailing slashes when missing for existing directories"""
        assert res["status_code"] == 301, f"Status expected `301`, returned `{res['status_code']}`"
        loc = res["headers"].get("location", "[ABSENT]")
        assert loc.endswith("/a2-test/2/"), f"`Location` expected to end with `/a2-test/2/`, returned `{loc}`"
        assert res["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"


    @make_request("get-path.http", PATH="/a2-test/1")
    def test_2_redirect_to_trailing_slash_for_directory_path(self, req, res):
        """Test whether redirects path to trailing slashes when missing for existing directories"""
        assert res["status_code"] == 301, f"Status expected `301`, returned `{res['status_code']}`"
        loc = res["headers"].get("location", "[ABSENT]")
        assert loc.endswith("/a2-test/1/"), f"`Location` expected to end with `/a2-test/1/`, returned `{loc}`"
        assert res["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"


    @make_request("get-url.http", PATH="/a2-test/2/")
    def test_2_get_default_index_file(self, req, res):
        """Test whether default index.html is returned instead of directory listing"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        req2, res2, errors = self.netcat("get-url.http", PATH="/a2-test/2/index.html")
        assert res2["status_code"] == 200, f"Status expected `200`, returned `{res2['status_code']}`"
        assert res["payload"] and res["payload"] == res2["payload"], f"Payload should contain contents of `/a2-test/2/index.html` file"
        assert res["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"


    @make_request("head-path.http", PATH="/a2-test/1/1.3/assignment1.ppt")
    def test_2_redirect_as_per_regexp_trailing_wildcard_capture(self, req, res):
        """Test whether redirects as per the regular expression with wildcard trailing capture group"""
        assert res["status_code"] == 302, f"Status expected `302`, returned `{res['status_code']}`"
        loc = res["headers"].get("location", "[ABSENT]")
        assert loc.endswith("/a2-test/1/1.1/assignment1.ppt"), f"`Location` expected to end with `/a2-test/1/1.1/assignment1.ppt`, returned `{loc}`"


    @make_request("head-path.http", PATH="/a2-test/coolcar.html")
    def test_2_redirect_as_per_regexp_trailing_specific_file(self, req, res):
        """Test whether redirects as per the regular expression with a specific trailing file name"""
        assert res["status_code"] == 302, f"Status expected `302`, returned `{res['status_code']}`"
        loc = res["headers"].get("location", "[ABSENT]")
        assert loc.endswith("/a2-test/galaxie.html"), f"`Location` expected to end with `/a2-test/galaxie.html`, returned `{loc}`"


    @make_request("head-path.http", PATH="/a2-test/galaxie.html")
    def test_2_dont_redirect_target_file(self, req, res):
        """Test whether the target of the configured redirect returns 200 OK"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="Fri, 20 Oct 2018 02:33:21 GMT")
    def test_2_conditional_head_fresh(self, req, res):
        """Test whether conditional HEAD of a fresh file returns 304 Not Modified"""
        assert res["status_code"] == 304, f"Status expected `304`, returned `{res['status_code']}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="Fri, 20 Oct 2018 02:33:20 GMT")
    def test_2_conditional_head_stale(self, req, res):
        """Test whether conditional HEAD of a stale file returns 200 OK"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="who-doesn't-want-a-fairlane?")
    def test_2_conditional_head_invalid_datetime(self, req, res):
        """Test whether conditional HEAD with invalid datetime returns 200 OK"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="2018-10-20 02:33:21.304307000 -0000")
    def test_2_conditional_head_unsupported_datetime_format(self, req, res):
        """Test whether conditional HEAD with unsupported datetime format returns 200 OK"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"


    @make_request("head-path.http", PATH="/a2-test/2/fairlane.html")
    def test_2_include_etag(self, req, res):
        """Test whether the HEAD response contains an ETag"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        assert "etag" in res["headers"], "`ETag` header should be present"
        etag = res["headers"].get("etag", "")
        assert etag.strip('"'), "`ETag` should not be empty"
        assert etag.strip('"') != etag, f'`ETag` should be in double quotes like `"{etag}"`, returned `{etag}`'


    @make_request("head-path.http", PATH="/a2-test/2/fairlane.html")
    def test_2_valid_etag_ok(self, req, res):
        """Test whether a valid ETag returns 200 OK"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        etag = res["headers"].get("etag", "").strip('"')
        assert etag, "`ETag` should not be empty"
        req2, res2, errors = self.netcat("get-if-match.http", PATH="/a2-test/2/fairlane.html", ETAG=etag)
        try:
            if not errors:
                assert res2["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
                ctype = res2["headers"].get("content-type", "[ABSENT]")
                assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
                assert res2["payload"] and b"1966 Ford Fairlane" in res2["payload"], "Payload should contain `1966 Ford Fairlane`"
        except AssertionError as e:
            errors.append(f"ASSERTION: {e}")
        return {"req": req2, "res": res2, "errors": errors}


    @make_request("get-if-match.http", PATH="/a2-test/2/fairlane.html", ETAG="203948kjaldsf002")
    def test_2_etag_if_match_failure(self, req, res):
        """Test whether a random ETag returns 412 Precondition Failed"""
        assert res["status_code"] == 412, f"Status expected `412`, returned `{res['status_code']}`"


    @make_request("head-keep-alive.http", PATH="/a2-test/2/index.html")
    def test_2_implicit_keep_alive(self, req, res):
        """Test whether the socket connection is kept alive by default"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"
        assert res["connection"] == "alive", "Socket connection should be kept `alive` due to no explicit `Connection: close` header"


    @make_request("trace-many-conditionals.http", PATH="/a2-test/2/index.html")
    def test_2_trace_unnecessary_conditionals(self, req, res):
        """Test whether many unnecessary conditionals are not processed"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("message/http"), f"`Content-Type` should start with `message/http`, returned `{ctype}`"
        assert res["payload"] and res["payload"].startswith(b"TRACE /a2-test/2/index.html HTTP/1.1"), f"Payload should start with `TRACE /a2-test/2/index.html HTTP/1.1`"


    @make_request("pipeline.http", PATH="/a2-test/", SUFFIX="2/index.html")
    def test_2_pipeline_requests(self, req, res):
        """Test whether multiple pipelined requests are processed and returned in the same order"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        pres, errors = self.parse_response(res["payload"])
        if errors:
            return {"req": req, "res": res, "errors": errors}
        assert pres["status_code"] == 200, f"Status expected `200`, returned `{pres['status_code']}`"
        ctype = pres["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        pres, errors = self.parse_response(pres["payload"])
        if errors:
            return {"req": req, "res": res, "errors": errors}
        assert pres["status_code"] == 200, f"Status expected `200`, returned `{pres['status_code']}`"
        ctype = pres["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert pres["payload"] and b"coolcar.html" in pres["payload"] and b"ford" in pres["payload"], "Payload should contain all file and folder names immediately under `/a2-test/` directory"
        assert res["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"


    @make_request("head-keep-alive.http", keep_alive=False, PATH="/a2-test/")
    def test_2_long_lived_connection(self, req, res):
        """Test whether the socket connection is kept alive to process multiple requests successively"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
        assert not res["payload"], f"Payload length expected `0` bytes, returned `{res['payload_size']}`"
        assert res["connection"] == "alive", "Socket connection should be kept `alive` due to no explicit `Connection: close` header"
        req2, res2, errors = self.netcat("head-keep-alive.http", keep_alive=True, PATH="/a2-test/2/index.html")
        req["raw"] += req2["raw"]
        res["connection"] = res2["connection"]
        pld = b""
        if res["payload"]:
            pld = res["payload"]
        pld += res2["raw_headers"].encode()
        if res2["payload"]:
            pld += res2["payload"]
        res["payload"] = pld
        try:
            if not errors:
                assert res2["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
                ctype = res2["headers"].get("content-type", "[ABSENT]")
                assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
                assert not res2["payload"], f"Payload length expected `0` bytes, returned `{res2['payload_size']}`"
                assert res2["connection"] == "alive", "Socket connection should be kept `alive` due to no explicit `Connection: close` header"
        except AssertionError as e:
            errors.append(f"ASSERTION: {e}")
        if errors:
            return {"req": req, "res": res, "errors": errors}
        req3, res3, errors = self.netcat("get-path.http", PATH="/a2-test/")
        req["raw"] += req3["raw"]
        res["connection"] = res3["connection"]
        res["payload"] += res3["raw_headers"].encode()
        if res3["payload"]:
            res["payload"] += res3["payload"]
        try:
            if not errors:
                assert res3["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
                ctype = res3["headers"].get("content-type", "[ABSENT]")
                assert ctype.startswith("text/html"), f"`Content-Type` should start with `text/html`, returned `{ctype}`"
                assert res3["payload"] and b"coolcar.html" in res3["payload"] and b"ford" in res3["payload"], "Payload should contain all file and folder names immediately under `/a2-test/` directory"
                assert res3["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"
        except AssertionError as e:
            errors.append(f"ASSERTION: {e}")
        return {"req": req, "res": res, "errors": errors}


    @make_request("get-path.http", PATH="/.well-known/access.log")
    def test_2_access_log_as_virtual_uri(self, req, res):
        """Test whether the access log is available as a Virtual URI in the Common Log Format"""
        assert res["status_code"] == 200, f"Status expected `200`, returned `{res['status_code']}`"
        ctype = res["headers"].get("content-type", "[ABSENT]")
        assert ctype.startswith("text/plain"), f"`Content-Type` should start with `text/plain`, returned `{ctype}`"


    @make_request("get-root.http")
    def test_42_the_untimate_question(self, req, res):
        """Answer to the Ultimate Question of Life, the Universe, and Everything"""
        assert False, "A placeholder test, meant to always fail!"


################################ END TEST CASES ################################


if __name__ == "__main__":
    def print_help():
        print("")
        print("Usage:")
        print("./tester.py [[<host>]:[<port>] [<test-id>|<assignment-numbers>]]")
        print("")
        print("<host>               : Hostname or IP address of the server to be tested (default: 'localhost')")
        print("<port>               : Port number of the server to be tested (default: '80')")
        print("<test-id>            : ID of an individual test function (e.g., 'test_0_healthy_server')")
        print("<assignment-numbers> : Comma separated list of assignment numbers (default: all assignments)")
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
        for batch, tests in HTTPTester().test_batches.items():
            for fname, func in tests.items():
                print(f"[Assignment {batch}] {colorize(fname)}: {colorize(func.__doc__, 96)}")
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

    batches = list(t.test_batches.keys())
    test_id = None
    if len(sys.argv) > 2:
        if t.TFPATTERN.match(sys.argv[2]):
            test_id = sys.argv[2]
        if re.match("^[\d,]+$", sys.argv[2]):
            batches = sys.argv[2].split(",")

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
            for batch in batches:
                for result in t.run_batch_tests(batch):
                    test_results[result["id"]] = "FAILED" if result["errors"] else "PASSED"
                    print_result(result)
            print_summary(hostport, test_results)
    except Exception as e:
        print(colorize(e))
