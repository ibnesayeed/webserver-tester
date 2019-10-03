import os
import random
import re

from ..base.httptester import HTTPTester


class CS531A1(HTTPTester):
    """CS531A1 is a special purpose HTTPTester with test cases for Assignment 1 of the CS531 (Web Server Design) course"""

    def __init__(self, hostport="localhost:80"):
        super().__init__(hostport=hostport)
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "messages", "cs531")
        self.USERAGENT = f"CS531 Assignment 1 Tester/{self.EPOCH}"
        self.clpattern = re.compile(r'^(?P<host>\S+)\s+(?P<identity>\S+)\s+(?P<user>\S+)\s+\[(?P<time>.+)\]\s+"(?P<request>.*)"\s+(?P<status>[0-9]+)\s+(?P<size>\S+)\s*$')
        self.ippattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        self.tmpattern = re.compile(r'^\d{2}\/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\/\d{4}:\d{2}:\d{2}:\d{2}\s(\+|\-)\d{4}$')
        self.stpattern = re.compile(r'^[1-5]\d{2}$')
        self.dgpattern = re.compile(r'^\d+$')


    @HTTPTester.request("get-url.http", PATH="/a1-test/2/index.html")
    def test_url_get_ok(self, report):
        """Test whether the URL of the assignment 1 directory returns HTTP/1.1 200 OK on GET"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 200)
        self.check_date_valid(report)


    @HTTPTester.request("method-url.http", METHOD="HEAD", PATH="/a1-test/2/index.html")
    def test_url_head_ok(self, report):
        """Test whether the URL of the assignment 1 directory returns 200 on HEAD"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_date_valid(report)
        self.check_payload_empty(report)


    @HTTPTester.request("method-path.http", METHOD="HEAD", PATH="/a1-test/2/index.html")
    def test_path_head_ok(self, report):
        """Test whether the relative path of the assignment 1 directory returns 200 on HEAD"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_date_valid(report)
        self.check_payload_empty(report)


    @HTTPTester.request("method-path.http", METHOD="OPTIONS", PATH="/a1-test/2/index.html")
    def test_path_options_ok(self, report):
        """Test whether the relative path of the assignment 1 directory returns 200 on OPTIONS"""
        self.check_status_is(report, 200)
        self.check_header_contains(report, "Allow", "GET")
        self.check_date_valid(report)


    @HTTPTester.request("get-path.http", PATH="/1/1.1/go%20hokies.html")
    def test_get_missing(self, report):
        """Test whether a non-existing path returns 404 on GET"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)
        self.check_date_valid(report)


    @HTTPTester.request("get-path.http", PATH="/a1-test/a1-test/")
    def test_get_duplicate_path_prefix(self, report):
        """Test tight path prefix checking"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)
        self.check_date_valid(report)


    @HTTPTester.request("unsupported-version.http", VERSION="HTTP/1.11")
    def test_unsupported_version(self, report):
        """Test whether a request with unsupported version returns 505"""
        self.check_status_is(report, 505)
        self.check_date_valid(report)


    @HTTPTester.request("invalid-request.http")
    def test_invalid_request(self, report):
        """Test whether an invalid request returns 400"""
        self.check_status_is(report, 400)
        self.check_date_valid(report)


    @HTTPTester.request("missing-host.http")
    def test_missing_host_header(self, report):
        """Test whether missing Host header in a request returns 400"""
        self.check_status_is(report, 400)
        self.check_date_valid(report)


    @HTTPTester.request("method-path.http", METHOD="POST", PATH="/a1-test/")
    def test_post_not_implemented(self, report):
        """Test whether the assignment 1 returns 501 on POST"""
        self.check_status_is(report, 501)
        self.check_date_valid(report)


    @HTTPTester.request("method-path-ua.http", METHOD="TRACE", PATH="/a1-test/1/1.4/")
    def test_trace_echoback(self, report):
        """Test whether the server echoes back the request on TRACE"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "message/http")
        self.check_date_valid(report)
        self.check_payload_begins(report, "TRACE /a1-test/1/1.4/ HTTP/1.1")
        self.check_payload_contains(report, f"User-Agent: {self.USERAGENT}", "Connection: close")


    @HTTPTester.request("get-url.http", PATH="/a1-test/1/1.4/test%3A.html")
    def test_get_escaped_file_name(self, report):
        """Test whether the escaped file name is respected"""
        self.check_status_is(report, 200)
        self.check_payload_contains(report, "lower case html")


    @HTTPTester.request("get-url.http", PATH="/a1-test/1/1.4/escape%25this.html")
    def test_get_escape_escaping_character(self, report):
        """Test whether the escaped escaping caracter in a file name is respected"""
        self.check_status_is(report, 200)
        self.check_payload_contains(report, "Go Monarchs!")


    @HTTPTester.request("get-url.http", PATH="/a1-test/2/0.jpeg")
    def test_get_jpeg_image(self, report):
        """Test whether a JPEG image returns 200 with proper Content-Length on GET"""
        self.check_status_is(report, 200)
        self.check_header_is(report, "Content-Length", "38457")
        self.check_payload_size(report, 38457)


    @HTTPTester.request("get-url.http", PATH="/a1-test/2/0.JPEG")
    def test_get_case_sensitive_file_extension(self, report):
        """Test whether file extensions are treated case-sensitive"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)


    @HTTPTester.request("get-url.http", PATH="/a1-test/4/thisfileisempty.txt")
    def test_get_empty_text_file(self, report):
        """Test whether an empty file returns zero bytes with 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "0")
        self.check_payload_empty(report)


    @HTTPTester.request("get-url.http", PATH="/a1-test/4/directory3isempty")
    def test_get_empty_unknown_file_directory(self, report):
        """Test whether an unknown empty file or directory returns zero bytes and a valid Content-Type with 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "application/octet-stream")
        self.check_header_is(report, "Content-Length", "0")
        self.check_payload_empty(report)


    @HTTPTester.request("get-url.http", PATH="/a1-test/1/1.2/arXiv.org.Idenitfy.repsonse.xml")
    def test_get_filename_with_many_dots(self, report):
        """Test whether file names with multiple dots return 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/xml")


    @HTTPTester.request("get-url.http", PATH="/a1-test/2/6.gif")
    def test_get_magic_cookie_of_a_binary_file(self, report):
        """Test whether a GIF file contains identifying magic cookie"""
        self.check_status_is(report, 200)
        self.check_payload_begins(report, "GIF89a")


    @HTTPTester.request("get-path.http", PATH="/.well-known/access.log")
    def test_access_log_as_virtual_uri(self, report):
        """Test whether the access log is available as a Virtual URI in the Common Log Format"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")
        self.check_payload_not_empty(report)
        line = random.choice(report["res"]["payload"].strip().decode().split("\n")).replace("\r", "")
        m = self.clpattern.match(line)
        assert m, f"Log entry `{line}` is not in Common Log format"
        report["notes"].append(f"Selected log entry `{line}`")
        record = m.groupdict()
        assert self.ippattern.match(record["host"]), f"`{record['host']}` is not a valid IP address"
        report["notes"].append(f"`{record['host']}` is a valid IP address")
        assert record["host"] != "0.0.0.0", f"`0.0.0.0` is not the IP address of the client"
        report["notes"].append(f"`{record['host']}` is potentially the IP address of a client")
        assert self.tmpattern.match(record["time"]), f"`{record['time']}` is not formatted as `%d/%b/%Y:%H:%M:%S %z`"
        report["notes"].append(f"`{record['time']}` is formatted correctly")
        assert self.stpattern.match(record["status"]), f"`{record['status']}` is not a valid status code"
        report["notes"].append(f"`{record['status']}` is a valid status code")
        assert self.dgpattern.match(record["size"]), f"`{record['size']}` is not a valid size"
        report["notes"].append(f"`{record['size']}` is a valid size")
