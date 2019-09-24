import os
import io
import re
import time
import random
import inspect
import collections
import functools
import socket


class HTTPTester():
    """HTTPTester is a generic HTTP server tester base class that can be inherited to write test cases for specific web servers"""

    def __init__(self, hostport="localhost:80"):
        """Initialize a HTTPTester instance for a server specified by the hostport"""

        # Directory where sample HTTP Message files are stored
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "messages")
        self.USERAGENT = "HTTP Tester"

        # Sources of noise in tests
        self.EPOCH = str(int(time.time()))
        self.RANDOMINT = str(random.randint(100, 10000))

        # Socket timeouts
        self.CONNECTION_TIMEOUT = 0.2
        self.SEND_DATA_TIMEOUT = 3.0
        self.RECV_FIRST_BYTE_TIMEOUT = 1.0
        self.RECV_END_TIMEOUT = 0.5
        self.LIFETIME_TIMEOUT = 5

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

        # Create a dict of all test cases
        self.testcases = {}
        tfuncs = [f for f in inspect.getmembers(self, inspect.ismethod) if f[0].startswith("test_")]
        for tf in tfuncs:
            tf[1].__func__.__orig_lineno__ = tf[1].__wrapped__.__code__.co_firstlineno if hasattr(tf[1], "__wrapped__") else tf[1].__code__.co_firstlineno
        for (fname, func) in sorted(tfuncs, key=lambda x: x[1].__orig_lineno__):
            self.testcases[fname] = func


    def req_obj(self):
        return {
            "raw": ""
        }


    def res_obj(self):
        return {
            "raw_headers": "",
            "http_version": "",
            "status_code": 0,
            "status_text": "",
            "headers": {},
            "payload": b"",
            "payload_size": 0,
            "connection": "closed"
        }


    def connect_sock(self):
        self.sock = socket.socket()
        self.sock.settimeout(self.CONNECTION_TIMEOUT)
        self.sock.connect((self.host, self.port))


    def reset_sock(self):
        if self.sock:
            self.sock.close()
            self.sock = None


    def netcat(self, msg_file, keep_alive=False, skip_parsing=False, **kwargs):
        report = {
            "req": self.req_obj(),
            "res": self.res_obj(),
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
                if skip_parsing:
                    report["res"]["raw_headers"] = b"".join(data).decode()
                else:
                    self.parse_response(b"".join(data), report)
        return report


    def replace_placeholders(self, msg, **kwargs):
        replacements = {
            "<HOST>": self.host,
            "<PORT>": str(self.port),
            "<HOSTPORT>": self.hostport,
            "<EPOCH>": self.EPOCH,
            "<RANDOMINT>": self.RANDOMINT,
            "<USERAGENT>": self.USERAGENT
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


    def slice_payload(self, msg, report):
        marker = 0
        dechunked = b""
        cl = report["res"]["headers"].get("content-length")
        if cl:
            try:
                marker = int(cl)
            except Exception as e:
                report["errors"].append(f"`Content-Length: {cl}` is not a valid number")
        elif report["res"]["headers"].get("transfer-encoding", "").endswith("chunked"):
            try:
                for chunk, marker in self.read_chunk(msg):
                    dechunked += chunk
            except Exception as e:
                report["errors"].append(str(e))
                marker = 0
        else:
            report["errors"].append("Neither `Content-Length` nor `Transfer-Encoding: chunked` header is provided to frame the payload")
        return msg[:marker], msg[marker:]


    def read_chunk(self, msg):
        s = io.BytesIO(msg)
        for chdesc in s:
            try:
                chsize = int(chdesc.split(b";")[0].strip(), 16)
            except Exception as e:
                cd = chdesc.decode().strip("\r\n")
                raise ValueError(f'Chunk descriptor `{cd}` must begin with a Hexadecimal number')
            ch = s.read(chsize)
            if s.readline() != b"\r\n":
                raise ValueError("Chunk is not terminated with a `CRLF`")
            yield ch, s.tell()
            if chsize == 0:
                return


    def parse_response(self, msg, report):
        if not msg.strip():
            report["res"] = self.res_obj()
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


    def parse_equal_sign_delimited_keys_values(self, str):
        kvreg = re.compile('([\w-]+)\s*=\s*"?([\w\s-]*)"?')
        return dict(kvreg.findall(str))


    def run_single_test(self, test_id):
        err = f"Test {test_id} not valid"
        if test_id.startswith("test_"):
            try:
                return self.testcases[test_id]()
            except KeyError as e:
                err = f"Test {test_id} not implemented"
        raise Exception(err)


    def run_all_tests(self):
        for fname, func in self.testcases.items():
            yield func()


    @classmethod
    def request(cls, msg_file, **kwargs):
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
                return {"id": func.__name__, "suite": self.__class__.__name__.lower(), "description": func.__doc__, "errors": report["errors"], "notes": report["notes"], "req": report["req"], "res": report["res"]}
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


    def check_header_absent(self, report, header):
        assert header.lower() not in report["res"]["headers"], f"`{header}` header should not be present"
        report["notes"].append(f"`{header}` header is absent")


    def check_header_is(self, report, header, value):
        self.check_header_present(report, header)
        val = report["res"]["headers"].get(header.lower(), "")
        assert value == val, f"`{header}` header should be `{value}`, returned `{val}`"
        report["notes"].append(f"`{header}` header has value `{value}`")


    def check_header_contains(self, report, header, *values):
        self.check_header_present(report, header)
        val = report["res"]["headers"].get(header.lower(), "")
        for value in values:
            assert value in val, f"`{header}` header should contain `{value}`, returned `{val}`"
            report["notes"].append(f"`{header}` header contains `{value}`")


    def check_header_doesnt_contain(self, report, header, *values):
        self.check_header_present(report, header)
        val = report["res"]["headers"].get(header.lower(), "")
        for value in values:
            assert value not in val, f"`{header}` header should not contain `{value}`, returned `{val}`"
            report["notes"].append(f"`{header}` header does not contain `{value}`")


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
        m = re.match(r'(W/)?"(\S+)"', etag)
        assert m, f"Expected non-empty double-quoted ASCII `ETag` string without any spaces, returned `{etag}`"
        assert not m[1], f"`Storng ETag` expected, returned `Weak ETag` as `{etag}`"
        report["notes"].append(f"`ETag` is not empty and properly formatted in double quotes as `{etag}`")


    def check_redirects_to(self, report, status, location):
        self.check_status_is(report, status)
        self.check_header_ends(report, "Location", location)


    def check_payload_empty(self, report):
        assert not report["res"]["payload"], f"Payload expected empty, returned `{report['res']['payload_size']}` bytes"
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


    def check_payload_contains(self, report, *values):
        for value in values:
            assert value.encode() in report["res"]["payload"], f"Payload should contain `{value}`"
            report["notes"].append(f"Payload contains `{value}`")


    def check_payload_doesnt_contain(self, report, *values):
        for value in values:
            assert value.encode() not in report["res"]["payload"], f"Payload should not contain `{value}`"
            report["notes"].append(f"Payload does not contain `{value}`")


    def check_payload_begins(self, report, value):
        assert report["res"]["payload"].startswith(value.encode()), f"Payload should begin with `{value}`"
        report["notes"].append(f"Payload begins with `{value}`")


    def check_payload_doesnt_begin(self, report, value):
        assert not report["res"]["payload"].startswith(value.encode()), f"Payload should not begin with `{value}`"
        report["notes"].append(f"Payload does not begin with `{value}`")


    def check_payload_ends(self, report, value):
        assert report["res"]["payload"].endswith(value.encode()), f"Payload should end with `{value}`"
        report["notes"].append(f"Payload ends with `{value}`")


    def check_connection_alive(self, report, explicit=False):
        reason = "explicit `Connection: keep-alive` header" if explicit else "no explicit `Connection: close` header"
        assert report["res"]["connection"] == "alive", f"Socket connection should be kept alive due to {reason}"
        report["notes"].append("Socket connection is kept alive")


    def check_connection_closed(self, report):
        assert report["res"]["connection"] == "closed", "Socket connection should be closed due to explicit `Connection: close` header"
        report["notes"].append("Socket connection is closed")
