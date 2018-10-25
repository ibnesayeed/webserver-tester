#!/usr/bin/env python3

import sys
import os
import re
import time
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
        self.LIFETIME_TIMEOUT = 15

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
        self.sock = socket.socket()
        self.sock.settimeout(self.CONNECTION_TIMEOUT)
        self.sock.connect((self.host, self.port))


    def reset_sock(self):
        if self.sock:
            self.sock.close()
            self.sock = None


    def netcat(self, msg_file, keep_alive=False, **kwargs):
        report = {
            "req": {
                "raw": ""
            },
            "res": {
                "raw_headers": "",
                "http_version": "",
                "status_code": 0,
                "status_text": "",
                "headers": {},
                "payload": b"",
                "payload_size": 0,
                "connection": "closed"
            },
            "errors": [],
            "notes": [],
        }
        with open(os.path.join(self.MSGDIR, msg_file), "rb") as f:
            msg = self.replace_placeholders(f.read(), **kwargs)
            hdrs, sep, pld = self.split_http_message(msg)
            msg = hdrs.replace(b"<PIPELINE>", b"").replace(b"\r", b"").replace(b"\n", b"\r\n") + b"\r\n\r\n" + pld
            report["req"]["raw"] = msg.decode()
            if self.sock:
                report["notes"].append(f"Reusing existing connection")
            else:
                report["notes"].append(f"Connecting to the `{self.host}:{self.port}` server")
                try:
                    self.connect_sock()
                except Exception as e:
                    report["errors"].append(f"Connection to the server `{self.host}:{self.port}` failed: {e}")
                    self.reset_sock()
                    return report
            try:
                self.sock.settimeout(self.SEND_DATA_TIMEOUT)
                self.sock.sendall(msg)
                report["notes"].append("Request data sent")
            except Exception as e:
                report["errors"].append(f"Sending data failed: {e}")
                keep_alive or self.reset_sock()
                return report
            try:
                data = []
                self.sock.settimeout(self.RECV_FIRST_BYTE_TIMEOUT)
                buf = self.sock.recv(4096)
                self.sock.settimeout(self.RECV_END_TIMEOUT)
                while buf:
                    data.append(buf)
                    buf = self.sock.recv(4096)
            except socket.timeout as e:
                report["res"]["connection"] = "alive"
            except Exception as e:
                report["errors"].append(f"Reading data failed: {e}")
            keep_alive or self.reset_sock()
            if not report["errors"]:
                report["notes"].append("Response data read")
                self.parse_response(b"".join(data), report)
        return report


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


    def parse_response(self, msg, report):
        if not msg.strip():
            report["errors"].append("Empty response")
            return
        hdrs, sep, pld = self.split_http_message(msg)
        report["res"]["payload"] = pld
        report["res"]["payload_size"] = len(pld)
        if not sep:
            report["errors"].append("Missing empty line after headers")
        if sep == b"\n\n":
            report["errors"].append("Using `LF` as header separator instead of `CRLF`")
        hdrs = hdrs.decode()
        report["res"]["raw_headers"] = hdrs
        hdrs = hdrs.replace("\r", "").replace("\n\t", "\t").replace("\n ", " ")
        lines = hdrs.split("\n")
        status_line = lines.pop(0)
        m = re.match("^([\w\/\.]+)\s+(\d+)\s+(.*)$", status_line)
        if m:
            report["res"]["http_version"] = m[1]
            report["res"]["status_code"] = int(m[2])
            report["res"]["status_text"] = m[3]
        else:
            report["errors"].append(f"Malformed status line `{status_line}`")
        for line in lines:
            kv = line.split(":", 1)
            if len(kv) < 2:
                report["errors"].append(f"Malformed header line `{line}`")
            else:
                k = kv[0].strip()
                if k != kv[0]:
                    report["errors"].append(f"Header name `{kv[0]}` has spurious white-spaces")
                report["res"]["headers"][k.lower()] = kv[1].strip()
        if not report["errors"]:
            report["notes"].append("Response parsed")


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
                report = self.netcat(msg_file, **kwargs)
                try:
                    if not report["errors"]:
                        func(self, report)
                except AssertionError as e:
                    report["errors"].append(f"ASSERTION: {e}")
                self.reset_sock()
                return {"id": func.__name__, "description": func.__doc__, "errors": report["errors"], "notes": report["notes"], "req": report["req"], "res": report["res"]}
            return wrapper
        return test_decorator


############################### ASSERTION HELPERS ##############################


    def check_status_is(self, report, status):
        sc = report["res"]["status_code"]
        assert status == sc, f"Status expected `{status}`, returned `{sc}`"
        report["notes"].append(f"Status is `{status}`")


    def check_version_is(self, report, version):
        ver = report["res"]["http_version"]
        assert version == ver, f"HTTP version expected `{version}`, returned `{ver}`"
        report["notes"].append(f"HTTP version is `{version}`")


    def check_header_present(self, report, header):
        assert header.lower() in report["res"]["headers"], f"`{header}` header should be present"
        report["notes"].append(f"`{header}` header is present")


    def check_header_is(self, report, header, value):
        self.check_header_present(report, header)
        val = report["res"]["headers"].get(header.lower(), "")
        assert value == val, f"`{header}` header should be `{value}`, returned `{val}`"
        report["notes"].append(f"`{header}` header has value `{value}`")


    def check_header_contains(self, report, header, value):
        self.check_header_present(report, header)
        val = report["res"]["headers"].get(header.lower(), "")
        assert value in val, f"`{header}` header should contain `{value}`, returned `{val}`"
        report["notes"].append(f"`{header}` header contains `{value}`")


    def check_header_begins(self, report, header, value):
        self.check_header_present(report, header)
        val = report["res"]["headers"].get(header.lower(), "")
        assert val.startswith(value), f"`{header}` header should begin with `{value}`, returned `{val}`"
        report["notes"].append(f"`{header}` header begins with `{value}`")


    def check_header_ends(self, report, header, value):
        self.check_header_present(report, header)
        val = report["res"]["headers"].get(header.lower(), "")
        assert val.endswith(value), f"`{header}` header should end with `{value}`, returned `{val}`"
        report["notes"].append(f"`{header}` header ends with `{value}`")


    def check_mime_is(self, report, value):
        self.check_header_begins(report, "Content-Type", value)


    def check_date_valid(self, report):
        self.check_header_present(report, "Date")
        datehdr = report["res"]["headers"].get("date", "")
        assert re.match("(Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} \d{2}:\d{2}:\d{2} GMT", datehdr), f"`Date: {datehdr}` is not in the preferred format as per `RCF7231 (section-7.1.1.1)`"
        report["notes"].append("`Date` header is in the preferred RCF7231 format")


    def check_etag_valid(self, report):
        self.check_header_present(report, "ETag")
        datehdr = report["res"]["headers"].get("etag", "")
        etag = report["res"]["headers"].get("etag", "")
        assert etag.strip('"'), "`ETag` should not be empty"
        assert etag.strip('"') != etag, f'`ETag` should be in double quotes like `"{etag}"`, returned `{etag}`'
        report["notes"].append("`ETag` is not empty and properly formatted in double quotes")


    def check_redirects_to(self, report, status, location):
        self.check_status_is(report, status)
        self.check_header_ends(report, "Location", location)


    def check_payload_empty(self, report):
        assert not report["res"]["payload"], f"Payload expected empty, returned `{res['payload_size']}` bytes"
        report["notes"].append("Payload is empty")


    def check_payload_not_empty(self, report):
        assert report["res"]["payload"], "Payload expected non-empty, returned empty"
        report["notes"].append("Payload is not empty")


    def check_payload_size(self, report, value):
        val = report["res"]["payload_size"]
        assert value == val, f"Payload size expected `{value}` bytes, returned `{val}`"
        report["notes"].append(f"Payload size is `{value}` bytes")


    def check_payload_is(self, report, value):
        assert value.encode() == report["res"]["payload"], f"Payload should exactly be `{value}`"
        report["notes"].append(f"Payload is exactly `{value}`")


    def check_payload_contains(self, report, value):
        assert value.encode() in report["res"]["payload"], f"Payload should contain `{value}`"
        report["notes"].append(f"Payload contains `{value}`")


    def check_payload_begins(self, report, value):
        assert report["res"]["payload"].startswith(value.encode()), f"Payload should begin with `{value}`"
        report["notes"].append(f"Payload begins with `{value}`")


    def check_payload_ends(self, report, value):
        assert report["res"]["payload"].endswith(value.encode()), f"Payload should end with `{value}`"
        report["notes"].append(f"Payload ends with `{value}`")


    def check_connection_alive(self, report, explicit=False):
        reason = "explicit `Connection: keep-alive` header" if explicit else "no explicit `Connection: close` header"
        assert report["res"]["connection"] == "alive", "Socket connection should be kept alive due to {reason}"
        report["notes"].append("Socket connection is kept alive")


    def check_connection_closed(self, report):
        assert report["res"]["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"
        report["notes"].append("Socket connection is closed")


############################### BEGIN TEST CASES ###############################


    @make_request("get-root.http")
    def test_0_healthy_server(self, report):
        """Test healthy server root"""
        self.check_status_is(report, 200)
        self.check_date_valid(report)
        self.check_header_present(report, "Content-Type")
        self.check_version_is(report, "HTTP/1.1")


    @make_request("malformed-header.http")
    def test_0_bad_request_header(self, report):
        """Test whether the server recognizes malformed headers"""
        self.check_status_is(report, 400)


    @make_request("get-url.http", PATH="/a1-test/2/index.html")
    def test_1_url_get_ok(self, report):
        """Test whether the URL of the assignment 1 directory returns HTTP/1.1 200 OK on GET"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 200)


    @make_request("method-url.http", METHOD="HEAD", PATH="/a1-test/2/index.html")
    def test_1_url_head_ok(self, report):
        """Test whether the URL of the assignment 1 directory returns 200 on HEAD"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @make_request("method-path.http", METHOD="HEAD", PATH="/a1-test/2/index.html")
    def test_1_path_head_ok(self, report):
        """Test whether the relative path of the assignment 1 directory returns 200 on HEAD"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @make_request("method-path.http", METHOD="OPTIONS", PATH="/a1-test/2/index.html")
    def test_1_path_options_ok(self, report):
        """Test whether the relative path of the assignment 1 directory returns 200 on OPTIONS"""
        self.check_status_is(report, 200)
        self.check_header_contains(report, "Allow", "GET")


    @make_request("get-path.http", PATH="/1/1.1/go%20hokies.html")
    def test_1_get_missing(self, report):
        """Test whether a non-existing path returns 404 on GET"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)


    @make_request("get-path.http", PATH="/a1-test/a1-test/")
    def test_1_get_duplicate_path_prefix(self, report):
        """Test tight path prefix checking"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)


    @make_request("unsupported-version.http", VERSION="HTTP/2.3")
    def test_1_unsupported_version(self, report):
        """Test whether a request with unsupported version returns 505"""
        self.check_status_is(report, 505)


    @make_request("unsupported-version.http", VERSION="HTTP/1.11")
    def test_1_tight_unsupported_version_check(self, report):
        """Test tight HTTP version checking to not match HTTP/1.11"""
        self.check_status_is(report, 505)


    @make_request("invalid-request.http")
    def test_1_invalid_request(self, report):
        """Test whether an invalid request returns 400"""
        self.check_status_is(report, 400)


    @make_request("missing-host.http")
    def test_1_missing_host_header(self, report):
        """Test whether missing Host header in a request returns 400"""
        self.check_status_is(report, 400)


    @make_request("method-path.http", METHOD="POST", PATH="/a1-test/")
    def test_1_post_not_implemented(self, report):
        """Test whether the assignment 1 returns 501 on POST"""
        self.check_status_is(report, 501)


    @make_request("method-path.http", METHOD="TRACE", PATH="/a1-test/1/1.4/")
    def test_1_trace_echoback(self, report):
        """Test whether the server echoes back the request on TRACE"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "message/http")
        self.check_payload_begins(report, "TRACE /a1-test/1/1.4/ HTTP/1.1")


    @make_request("get-url.http", PATH="/a1-test/1/1.4/test%3A.html")
    def test_1_get_escaped_file_name(self, report):
        """Test whether the escaped file name is respected"""
        self.check_status_is(report, 200)
        self.check_payload_contains(report, "lower case html")


    @make_request("get-url.http", PATH="/a1-test/1/1.4/escape%25this.html")
    def test_1_get_escape_escaping_character(self, report):
        """Test whether the escaped escaping caracter in a file name is respected"""
        self.check_status_is(report, 200)
        self.check_payload_contains(report, "Go Monarchs!")


    @make_request("get-url.http", PATH="/a1-test/2/0.jpeg")
    def test_1_get_jpeg_image(self, report):
        """Test whether a JPEG image returns 200 with proper Content-Length on GET"""
        self.check_status_is(report, 200)
        self.check_header_is(report, "Content-Length", "38457")
        self.check_payload_size(report, 38457)


    @make_request("get-url.http", PATH="/a1-test/2/0.JPEG")
    def test_1_get_case_sensitive_file_extension(self, report):
        """Test whether file extensions are treated case-sensitive"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)


    @make_request("get-url.http", PATH="/a1-test/4/thisfileisempty.txt")
    def test_1_get_empty_text_file(self, report):
        """Test whether an empty file returns zero bytes with 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "0")
        self.check_payload_empty(report)


    @make_request("get-url.http", PATH="/a1-test/4/directory3isempty")
    def test_1_get_empty_directory(self, report):
        """Test whether an empty directory returns zero bytes and a valid Content-Type with 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "application/octet-stream")
        self.check_header_is(report, "Content-Length", "0")
        self.check_payload_empty(report)


    @make_request("get-url.http", PATH="/a1-test/1/1.2/arXiv.org.Idenitfy.repsonse.xml")
    def test_1_get_filename_with_many_dots(self, report):
        """Test whether file names with multiple dots return 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/xml")


    @make_request("get-url.http", PATH="/a1-test/2/6.gif")
    def test_1_get_magic_cookie_of_a_binary_file(self, report):
        """Test whether a GIF file contains identifying magic cookie"""
        self.check_status_is(report, 200)
        self.check_payload_begins(report, "GIF89a")


    @make_request("get-url.http", PATH="/a2-test/")
    def test_2_get_directory_listing(self, report):
        """Test whether a2-test directory root returns directory listing"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_contains(report, "coolcar.html")
        self.check_payload_contains(report, "ford")
        self.check_connection_closed(report)


    @make_request("get-url.http", PATH="/a2-test/2")
    def test_2_redirect_to_trailing_slash_for_directory_url(self, report):
        """Test whether redirects URL to trailing slashes when missing for existing directories"""
        self.check_redirects_to(report, 301, "/a2-test/2/")
        self.check_connection_closed(report)


    @make_request("get-path.http", PATH="/a2-test/1")
    def test_2_redirect_to_trailing_slash_for_directory_path(self, report):
        """Test whether redirects path to trailing slashes when missing for existing directories"""
        self.check_redirects_to(report, 301, "/a2-test/1/")
        self.check_connection_closed(report)


    @make_request("get-url.http", PATH="/a2-test/2/")
    def test_2_get_default_index_file(self, report):
        """Test whether default index.html is returned instead of directory listing"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_not_empty(report)
        report["notes"].append("Fetching `/a2-test/2/index.html` for content comparison")
        report2 = self.netcat("get-url.http", PATH="/a2-test/2/index.html")
        self.check_status_is(report2, 200)
        assert report["res"]["payload"] == report2["res"]["payload"], f"Payload should contain contents of `/a2-test/2/index.html` file"
        report["notes"].append("Contents of `/a2-test/2/` and `/a2-test/2/index.html` are the same")
        self.check_connection_closed(report)


    @make_request("head-path.http", PATH="/a2-test/1/1.3/assignment1.ppt")
    def test_2_redirect_as_per_regexp_trailing_wildcard_capture(self, report):
        """Test whether redirects as per the regular expression with wildcard trailing capture group"""
        self.check_redirects_to(report, 302, "/a2-test/1/1.1/assignment1.ppt")


    @make_request("head-path.http", PATH="/a2-test/coolcar.html")
    def test_2_redirect_as_per_regexp_trailing_specific_file(self, report):
        """Test whether redirects as per the regular expression with a specific trailing file name"""
        self.check_redirects_to(report, 302, "/a2-test/galaxie.html")


    @make_request("head-path.http", PATH="/a2-test/galaxie.html")
    def test_2_dont_redirect_target_file(self, report):
        """Test whether the target of the configured redirect returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @make_request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="Sat, 20 Oct 2018 02:33:21 GMT")
    def test_2_conditional_head_fresh(self, report):
        """Test whether conditional HEAD of a fresh file returns 304 Not Modified"""
        self.check_status_is(report, 304)
        self.check_payload_empty(report)


    @make_request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="Sat, 20 Oct 2018 02:33:20 GMT")
    def test_2_conditional_head_stale(self, report):
        """Test whether conditional HEAD of a stale file returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @make_request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="who-doesn't-want-a-fairlane?")
    def test_2_conditional_head_invalid_datetime(self, report):
        """Test whether conditional HEAD with invalid datetime returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @make_request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="2018-10-20 02:33:21.304307000 -0000")
    def test_2_conditional_head_unsupported_datetime_format(self, report):
        """Test whether conditional HEAD with unsupported datetime format returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @make_request("head-path.http", PATH="/a2-test/2/fairlane.html")
    def test_2_include_etag(self, report):
        """Test whether the HEAD response contains an ETag"""
        self.check_status_is(report, 200)
        self.check_etag_valid(report)


    @make_request("head-path.http", PATH="/a2-test/2/fairlane.html")
    def test_2_valid_etag_ok(self, report):
        """Test whether a valid ETag returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_etag_valid(report)
        etag = report["res"]["headers"].get("etag", "").strip('"')
        report["notes"].append(f"`ETag` fetched for reuse as `{etag}` in the next request")
        report2 = self.netcat("get-if-match.http", PATH="/a2-test/2/fairlane.html", ETAG=etag)
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_contains(report, "1966 Ford Fairlane")


    @make_request("get-if-match.http", PATH="/a2-test/2/fairlane.html", ETAG="203948kjaldsf002")
    def test_2_etag_if_match_failure(self, report):
        """Test whether a random ETag returns 412 Precondition Failed"""
        self.check_status_is(report, 412)


    @make_request("head-keep-alive.http", keep_alive=True, PATH="/a2-test/2/index.html")
    def test_2_implicit_keep_alive_until_timeout(self, report):
        """Test whether the socket connection is kept alive by default and closed after the set timeout"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)
        self.check_connection_alive(report)
        time.sleep(self.LIFETIME_TIMEOUT + 1)
        report["notes"].append(f"Making a sebsequent request after `{self.LIFETIME_TIMEOUT}` seconds")
        report2 = self.netcat("head-keep-alive.http", PATH="/a2-test/2/index.html")
        report["req"]["raw"] += report2["req"]["raw"]
        report["res"]["raw_headers"] += "\r\n\r\n" + report2["res"]["raw_headers"]
        report["res"]["payload"] = report2["res"]["payload"]
        report["res"]["payload_size"] = len(report2["res"]["payload"])
        report["res"]["connection"] = report2["res"]["connection"]
        try:
            assert not report2["errors"], "Second response should be a valid `408 Request Timeout`"
            self.check_status_is(report2, 408)
            self.check_header_is(report2, "Connection", "close")
            self.check_connection_closed(report2)
            report["notes"] += report2["notes"]
        except AssertionError:
            report["errors"] = report2["errors"]
            report["notes"] += report2["notes"]
            raise


    @make_request("trace-many-conditionals.http", PATH="/a2-test/2/index.html")
    def test_2_trace_unnecessary_conditionals(self, report):
        """Test whether many unnecessary conditionals are not processed"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "message/http")
        self.check_payload_begins(report, "TRACE /a2-test/2/index.html HTTP/1.1")


    @make_request("pipeline.http", PATH="/a2-test/", SUFFIX="2/index.html")
    def test_2_pipeline_requests(self, report):
        """Test whether multiple pipelined requests are processed and returned in the same order"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        orig_hdr = report["res"]["raw_headers"]
        orig_pld = report["res"]["payload"]
        try:
            report["notes"].append("Parsing second response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Second response should be a valid HTTP Message"
            self.check_status_is(report, 200)
            self.check_mime_is(report, "text/html")
            report["notes"].append("Parsing third response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Third response should be a valid HTTP Message"
            self.check_status_is(report, 200)
            self.check_mime_is(report, "text/html")
            self.check_payload_contains(report, "coolcar.html")
            self.check_payload_contains(report, "ford")
            self.check_connection_closed(report)
        except AssertionError:
            report["res"]["raw_headers"] = orig_hdr
            report["res"]["payload"] = orig_pld
            raise
        report["res"]["raw_headers"] = orig_hdr
        report["res"]["payload"] = orig_pld


    @make_request("head-keep-alive.http", keep_alive=True, PATH="/a2-test/")
    def test_2_long_lived_connection(self, report):
        """Test whether the socket connection is kept alive to process multiple requests successively"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)
        self.check_connection_alive(report)
        report["notes"].append("Making second request")
        report2 = self.netcat("head-keep-alive.http", keep_alive=True, PATH="/a2-test/2/index.html")
        report["req"]["raw"] += report2["req"]["raw"]
        report["res"]["raw_headers"] += "\r\n\r\n" + report2["res"]["raw_headers"]
        report["res"]["payload"] = report2["res"]["payload"]
        report["res"]["payload_size"] = len(report2["res"]["payload"])
        report["res"]["connection"] = report2["res"]["connection"]
        try:
            assert not report2["errors"], "Second response should be a valid HTTP Message"
            self.check_status_is(report2, 200)
            self.check_mime_is(report2, "text/html")
            self.check_payload_empty(report2)
            self.check_connection_alive(report2)
            report["notes"] += report2["notes"]
        except AssertionError:
            report["errors"] = report2["errors"]
            report["notes"] += report2["notes"]
            raise
        report["notes"].append("Making third request")
        report3 = self.netcat("get-path.http", PATH="/a2-test/")
        report["req"]["raw"] += report3["req"]["raw"]
        report["res"]["raw_headers"] += "\r\n\r\n" + report3["res"]["raw_headers"]
        report["res"]["payload"] = report3["res"]["payload"]
        report["res"]["payload_size"] = len(report3["res"]["payload"])
        report["res"]["connection"] = report3["res"]["connection"]
        try:
            assert not report3["errors"], "Third response should be a valid HTTP Message"
            self.check_status_is(report3, 200)
            self.check_mime_is(report3, "text/html")
            self.check_payload_contains(report3, "coolcar.html")
            self.check_payload_contains(report3, "ford")
            self.check_connection_closed(report3)
            report["notes"] += report3["notes"]
        except AssertionError:
            report["errors"] = report3["errors"]
            report["notes"] += report3["notes"]
            raise


    @make_request("get-path.http", PATH="/.well-known/access.log")
    def test_2_access_log_as_virtual_uri(self, report):
        """Test whether the access log is available as a Virtual URI in the Common Log Format"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")


    @make_request("get-root.http")
    def test_42_the_untimate_question(self, report):
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

    def print_result(result, print_text_payload=False):
        print("-" * 79)
        print(f"{result['id']}: {colorize(result['description'], 96)}")
        for note in result["notes"]:
            print(f"* {note}")
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
            if print_text_payload and result["res"]["headers"].get("content-type", "text/plain").split('/')[0] in ["text", "message"]:
                print(result["res"]["payload"].decode())
            else:
                print(f"* [Payload redacted ({result['res']['payload_size']} bytes)]")
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
            print_result(result, print_text_payload=True)
        else:
            test_results = {}
            for batch in batches:
                for result in t.run_batch_tests(batch):
                    test_results[result["id"]] = "FAILED" if result["errors"] else "PASSED"
                    print_result(result)
            print_summary(hostport, test_results)
    except Exception as e:
        print(colorize(e))
