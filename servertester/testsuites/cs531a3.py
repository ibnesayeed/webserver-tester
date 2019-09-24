import os

from ..base.httptester import HTTPTester


class CS531A3(HTTPTester):
    """CS531A3 is a special purpose HTTPTester with test cases for Assignment 3 of the CS531 (Web Server Design) course"""

    def __init__(self, hostport="localhost:80"):
        super().__init__(hostport=hostport)
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "messages", "cs531")
        self.USERAGENT = f"CS531 Assignment 3 Tester/{self.EPOCH}"


    @HTTPTester.request("get-url-ua.http", PATH="/a3-test/fairlane.txt")
    def test_useragent_get_text_ok(self, report):
        """Test whether a request with a custom user-agent returns OK with corresponding text response"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "193")
        self.check_payload_contains(report, "______________")


    @HTTPTester.request("get-url-range-referer.http", PATH="/a3-test/index.html", SUFFIX=".es", RANGE="bytes=0-99")
    def test_partial_content_range_language(self, report):
        """Test whether a valid range request header returns partial content in a specific langaue"""
        self.check_status_is(report, 206)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Content-Language", "es")
        self.check_header_present(report, "Content-Range")
        self.check_header_is(report, "Content-Length", "100")
        self.check_payload_size(report, 100)


    @HTTPTester.request("get-path-ua.http", PATH="/a3-test/index.htmll")
    def test_chunked_404(self, report):
        """Test whether a 404 Not Found page returns chunked encoded HTML"""
        self.check_status_is(report, 404)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_not_empty(report)


    @HTTPTester.request("conditional-head.http", PATH="/a3-test/fairlane.gif", MODTIME="Sat, 10 Nov 2018 20:46:11 GMT")
    def test_conditional_head_image_fresh(self, report):
        """Test whether conditional HEAD of a fresh image file returns 304 Not Modified"""
        self.check_status_is(report, 304)
        self.check_payload_empty(report)


    @HTTPTester.request("conditional-head.http", PATH="/a3-test/fairlane.gif", MODTIME="Sat, 27 Oct 2018 20:46:09 GMT")
    def test_conditional_head_image_stale(self, report):
        """Test whether conditional HEAD of a stale image file returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "image/gif")
        self.check_payload_empty(report)


    @HTTPTester.request("head-path.http", PATH="/a3-test/fairlane")
    def test_no_accept_header_multiple_choices(self, report):
        """Test whether missing Accept header yields multiple choices"""
        self.check_status_is(report, 300)
        self.check_header_present(report, "Alternates")
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_empty(report)


    @HTTPTester.request("get-path-accept.http", PATH="/a3-test/fairlane", ACCEPT="image/*; q=1.0")
    def test_ambiguous_accept_header_multiple_choices(self, report):
        """Test whether an Accept header with the same qvalue for all image types yields multiple choices"""
        self.check_status_is(report, 300)
        self.check_header_present(report, "Alternates")
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_not_empty(report)


    @HTTPTester.request("head-path-accept.http", PATH="/a3-test/fairlane", ACCEPT="image/jpeg; q=0.9, image/png; q=0.91, image/tiff; q=0.95")
    def test_accept_header_png_ok(self, report):
        """Test whether an Accept header with unique qvalue returns a PNG"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "image/png")
        self.check_header_is(report, "Content-Length", "98203")
        self.check_payload_empty(report)


    @HTTPTester.request("head-path-accept.http", PATH="/a3-test/fairlane", ACCEPT="text/*; q=1.0, image/*; q=0.99")
    def test_accept_header_text_ok(self, report):
        """Test whether an Accept header with high qvalue returns plain text"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "193")
        self.check_payload_empty(report)


    @HTTPTester.request("head-path-accept-attr.http", PATH="/a3-test/vt-uva.html", ACCEPTATTR="Encoding", ACCEPTVAL="compress; q=0.0, gzip; q=0.0, deflate; q=0.5")
    def test_not_accptable_encoding(self, report):
        """Test whether explicit zero qvalue for all supported encodings returns 406 Not Acceptable"""
        self.check_status_is(report, 406)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_empty(report)


    @HTTPTester.request("head-path-accept-attr.http", PATH="/a3-test/vt-uva.html.Z", ACCEPTATTR="Encoding", ACCEPTVAL="compress; q=0.0, gzip; q=0.5")
    def test_explicit_extention_ignore_content_negotiation(self, report):
        """Test whether an explicit existing file extension ignores content negotiation"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Content-Encoding", "compress")
        self.check_header_is(report, "Content-Length", "42757")
        self.check_payload_empty(report)


    @HTTPTester.request("head-path-accept-attr.http", PATH="/a3-test/index.html", ACCEPTATTR="Language", ACCEPTVAL="en; q=1.0, de; q=1.0, fr; q=1.0")
    def test_ambiguous_accept_language_multiple_choices(self, report):
        """Test whether an Accept-Language header with the same qvalue for more than one available languages yields multiple choices"""
        self.check_status_is(report, 300)
        self.check_header_present(report, "Alternates")
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_empty(report)


    @HTTPTester.request("head-path-accept-language-charset.http", PATH="/a3-test/index.html.ja", LANGUAGE="en; q=1.0, ja; q=0.5", CHARSET="euc-jp; q=1.0, iso-2022-jp; q=0.0")
    def test_not_accptable_incompatiple_charset(self, report):
        """Test whether explicit zero qvalue of charset associated with the explicit language extension returns 406 Not Acceptable"""
        self.check_status_is(report, 406)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_empty(report)


    @HTTPTester.request("method-path-range.http", METHOD="GET", PATH="/a3-test/fairlane.txt", RANGE="bytes=10-20")
    def test_partial_content_range_text(self, report):
        """Test whether a valid range request header returns partial content in plain text"""
        self.check_status_is(report, 206)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Range", "bytes 10-20/193")
        self.check_header_is(report, "Content-Length", "11")
        self.check_payload_size(report, 11)


    @HTTPTester.request("get-if-match.http", PATH="/a3-test/fairlane.txt", ETAG="20933948kjaldsf000002")
    def test_etag_precondition_failure(self, report):
        """Test whether a random If-Match ETag returns 412 Precondition Failed"""
        self.check_status_is(report, 412)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_not_empty(report)


    @HTTPTester.request("get-path-ua.http", PATH="/a3-test/index.html.ru.koi8-r")
    def test_explicit_language_charset_etag(self, report):
        """Test whether explicit language and charset as extensions returns ETag and Content-Type with charset"""
        self.check_status_is(report, 200)
        self.check_header_is(report, "Content-Type", "text/html; charset=koi8-r")
        self.check_header_is(report, "Content-Language", "ru")
        self.check_etag_valid(report)
        self.check_payload_size(report, 7277)


    @HTTPTester.request("get-path-ua.http", PATH="/a3-test/index.html.ru.koi8-r")
    def test_valid_etag_conditional_get(self, report):
        """Test whether conditional GET with a valid ETag returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_etag_valid(report)
        etag = report["res"]["headers"].get("etag", "").strip('"')
        report["notes"].append(f'`ETag` fetched for reuse as `"{etag}"` in the subsequent request')
        report2 = self.netcat("get-if-match.http", PATH="/a3-test/index.html.ru.koi8-r", ETAG=etag)
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Content-Type", "text/html; charset=koi8-r")
        self.check_header_is(report, "Content-Language", "ru")
        self.check_payload_size(report, 7277)


    @HTTPTester.request("pipeline-range.http", PATH="/a3-test/index.html", SUFFIX1=".en", SUFFIX2=".ja.jis")
    def test_pipeline_range_negotiate(self, report):
        """Test whether multiple pipelined requests with content negotiations are processed and returned in the same order"""
        self.check_status_is(report, 206)
        self.check_mime_is(report, "text/html")
        self.check_header_present(report, "Content-Range")
        self.check_header_is(report, "Content-Length", "100")
        orig_hdr = report["res"]["raw_headers"]
        try:
            report["notes"].append("Parsing second response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Second response should be a valid HTTP Message"
            self.check_status_is(report, 300)
            self.check_header_present(report, "Alternates")
            self.check_mime_is(report, "text/html")
            self.check_header_is(report, "Transfer-Encoding", "chunked")
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
            report["notes"].append("Parsing third response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Third response should be a valid HTTP Message"
            self.check_status_is(report, 200)
            self.check_header_is(report, "Content-Type", "text/html; charset=iso-2022-jp")
            self.check_header_is(report, "Content-Language", "ja")
            self.check_header_is(report, "Content-Length", "7635")
            self.check_payload_empty(report)
            self.check_connection_closed(report)
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
        except AssertionError:
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
            report["res"]["raw_headers"] = orig_hdr
            raise
        report["res"]["raw_headers"] = orig_hdr
