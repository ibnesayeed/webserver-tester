import time

from ..base.httptester import HTTPTester


class CS531A1(HTTPTester):
    """CS531A1 is a special purpose HTTPTester with test cases for Assignment 1 of the CS531 (Web Server Design) course"""


    @HTTPTester.request("get-url.http", PATH="/a1-test/2/index.html")
    def test_1_url_get_ok(self, report):
        """Test whether the URL of the assignment 1 directory returns HTTP/1.1 200 OK on GET"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 200)


    @HTTPTester.request("method-url.http", METHOD="HEAD", PATH="/a1-test/2/index.html")
    def test_1_url_head_ok(self, report):
        """Test whether the URL of the assignment 1 directory returns 200 on HEAD"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @HTTPTester.request("method-path.http", METHOD="HEAD", PATH="/a1-test/2/index.html")
    def test_1_path_head_ok(self, report):
        """Test whether the relative path of the assignment 1 directory returns 200 on HEAD"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @HTTPTester.request("method-path.http", METHOD="OPTIONS", PATH="/a1-test/2/index.html")
    def test_1_path_options_ok(self, report):
        """Test whether the relative path of the assignment 1 directory returns 200 on OPTIONS"""
        self.check_status_is(report, 200)
        self.check_header_contains(report, "Allow", "GET")


    @HTTPTester.request("get-path.http", PATH="/1/1.1/go%20hokies.html")
    def test_1_get_missing(self, report):
        """Test whether a non-existing path returns 404 on GET"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)


    @HTTPTester.request("get-path.http", PATH="/a1-test/a1-test/")
    def test_1_get_duplicate_path_prefix(self, report):
        """Test tight path prefix checking"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)


    @HTTPTester.request("unsupported-version.http", VERSION="HTTP/2.3")
    def test_1_unsupported_version(self, report):
        """Test whether a request with unsupported version returns 505"""
        self.check_status_is(report, 505)


    @HTTPTester.request("unsupported-version.http", VERSION="HTTP/1.11")
    def test_1_tight_unsupported_version_check(self, report):
        """Test tight HTTP version checking to not match HTTP/1.11"""
        self.check_status_is(report, 505)


    @HTTPTester.request("invalid-request.http")
    def test_1_invalid_request(self, report):
        """Test whether an invalid request returns 400"""
        self.check_status_is(report, 400)


    @HTTPTester.request("missing-host.http")
    def test_1_missing_host_header(self, report):
        """Test whether missing Host header in a request returns 400"""
        self.check_status_is(report, 400)


    @HTTPTester.request("method-path.http", METHOD="POST", PATH="/a1-test/")
    def test_1_post_not_implemented(self, report):
        """Test whether the assignment 1 returns 501 on POST"""
        self.check_status_is(report, 501)


    @HTTPTester.request("method-path.http", METHOD="TRACE", PATH="/a1-test/1/1.4/")
    def test_1_trace_echoback(self, report):
        """Test whether the server echoes back the request on TRACE"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "message/http")
        self.check_payload_begins(report, "TRACE /a1-test/1/1.4/ HTTP/1.1")


    @HTTPTester.request("get-url.http", PATH="/a1-test/1/1.4/test%3A.html")
    def test_1_get_escaped_file_name(self, report):
        """Test whether the escaped file name is respected"""
        self.check_status_is(report, 200)
        self.check_payload_contains(report, "lower case html")


    @HTTPTester.request("get-url.http", PATH="/a1-test/1/1.4/escape%25this.html")
    def test_1_get_escape_escaping_character(self, report):
        """Test whether the escaped escaping caracter in a file name is respected"""
        self.check_status_is(report, 200)
        self.check_payload_contains(report, "Go Monarchs!")


    @HTTPTester.request("get-url.http", PATH="/a1-test/2/0.jpeg")
    def test_1_get_jpeg_image(self, report):
        """Test whether a JPEG image returns 200 with proper Content-Length on GET"""
        self.check_status_is(report, 200)
        self.check_header_is(report, "Content-Length", "38457")
        self.check_payload_size(report, 38457)


    @HTTPTester.request("get-url.http", PATH="/a1-test/2/0.JPEG")
    def test_1_get_case_sensitive_file_extension(self, report):
        """Test whether file extensions are treated case-sensitive"""
        self.check_version_is(report, "HTTP/1.1")
        self.check_status_is(report, 404)


    @HTTPTester.request("get-url.http", PATH="/a1-test/4/thisfileisempty.txt")
    def test_1_get_empty_text_file(self, report):
        """Test whether an empty file returns zero bytes with 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "0")
        self.check_payload_empty(report)


    @HTTPTester.request("get-url.http", PATH="/a1-test/4/directory3isempty")
    def test_1_get_empty_directory(self, report):
        """Test whether an empty directory returns zero bytes and a valid Content-Type with 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "application/octet-stream")
        self.check_header_is(report, "Content-Length", "0")
        self.check_payload_empty(report)


    @HTTPTester.request("get-url.http", PATH="/a1-test/1/1.2/arXiv.org.Idenitfy.repsonse.xml")
    def test_1_get_filename_with_many_dots(self, report):
        """Test whether file names with multiple dots return 200 on GET"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/xml")


    @HTTPTester.request("get-url.http", PATH="/a1-test/2/6.gif")
    def test_1_get_magic_cookie_of_a_binary_file(self, report):
        """Test whether a GIF file contains identifying magic cookie"""
        self.check_status_is(report, 200)
        self.check_payload_begins(report, "GIF89a")
