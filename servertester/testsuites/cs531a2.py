import os
import time

from ..base.httptester import HTTPTester


class CS531A2(HTTPTester):
    """CS531A2 is a special purpose HTTPTester with test cases for Assignment 2 of the CS531 (Web Server Design) course"""

    def __init__(self, hostport="localhost:80"):
        super().__init__(hostport=hostport)
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "messages", "cs531")
        self.USERAGENT = f"CS531 Assignment 2 Tester/{self.EPOCH}"


    @HTTPTester.request("get-url.http", PATH="/a2-test/")
    def test_get_directory_listing(self, report):
        """Test whether a2-test directory root returns directory listing"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_contains(report, "coolcar.html", "ford")
        self.check_connection_closed(report)


    @HTTPTester.request("get-url.http", PATH="/a2-test/2")
    def test_redirect_to_trailing_slash_for_directory_url(self, report):
        """Test whether redirects URL to trailing slashes when missing for existing directories"""
        self.check_redirects_to(report, 301, "/a2-test/2/")
        self.check_connection_closed(report)


    @HTTPTester.request("get-path.http", PATH="/a2-test/1")
    def test_redirect_to_trailing_slash_for_directory_path(self, report):
        """Test whether redirects path to trailing slashes when missing for existing directories"""
        self.check_redirects_to(report, 301, "/a2-test/1/")
        self.check_connection_closed(report)


    @HTTPTester.request("get-url.http", PATH="/a2-test/2/")
    def test_get_default_index_file(self, report):
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


    @HTTPTester.request("head-path.http", PATH="/a2-test/1/1.3/assignment1.ppt")
    def test_redirect_as_per_regexp_trailing_wildcard_capture(self, report):
        """Test whether redirects as per the regular expression with wildcard trailing capture group"""
        self.check_redirects_to(report, 302, "/a2-test/1/1.1/assignment1.ppt")


    @HTTPTester.request("head-path.http", PATH="/a2-test/coolcar.html")
    def test_redirect_as_per_regexp_trailing_specific_file(self, report):
        """Test whether redirects as per the regular expression with a specific trailing file name"""
        self.check_redirects_to(report, 302, "/a2-test/galaxie.html")


    @HTTPTester.request("head-path.http", PATH="/a2-test/galaxie.html")
    def test_dont_redirect_target_file(self, report):
        """Test whether the target of the configured redirect returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @HTTPTester.request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="Sat, 20 Oct 2018 02:33:21 GMT")
    def test_conditional_head_fresh(self, report):
        """Test whether conditional HEAD of a fresh file returns 304 Not Modified"""
        self.check_status_is(report, 304)
        self.check_payload_empty(report)


    @HTTPTester.request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="Sat, 20 Oct 2018 02:33:20 GMT")
    def test_conditional_head_stale(self, report):
        """Test whether conditional HEAD of a stale file returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @HTTPTester.request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="who-doesn't-want-a-fairlane?")
    def test_conditional_head_invalid_datetime(self, report):
        """Test whether conditional HEAD with invalid datetime returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @HTTPTester.request("conditional-head.http", PATH="/a2-test/2/fairlane.html", MODTIME="2018-10-20 02:33:21.304307000 -0000")
    def test_conditional_head_unsupported_datetime_format(self, report):
        """Test whether conditional HEAD with unsupported datetime format returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)


    @HTTPTester.request("head-path.http", PATH="/a2-test/2/fairlane.html")
    def test_include_etag(self, report):
        """Test whether the HEAD response contains an ETag"""
        self.check_status_is(report, 200)
        self.check_etag_valid(report)


    @HTTPTester.request("head-path.http", PATH="/a2-test/2/fairlane.html")
    def test_valid_etag_ok(self, report):
        """Test whether a valid ETag returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_etag_valid(report)
        etag = report["res"]["headers"].get("etag", "").strip('"')
        report["notes"].append(f'`ETag` fetched for reuse as `"{etag}"` in the subsequent request')
        report2 = self.netcat("get-if-match.http", PATH="/a2-test/2/fairlane.html", ETAG=etag)
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_contains(report, "1966 Ford Fairlane")


    @HTTPTester.request("get-if-match.http", PATH="/a2-test/2/fairlane.html", ETAG="203948kjaldsf002")
    def test_etag_if_match_failure(self, report):
        """Test whether a random ETag returns 412 Precondition Failed"""
        self.check_status_is(report, 412)


    @HTTPTester.request("head-keep-alive.http", keep_alive=True, PATH="/a2-test/2/index.html")
    def test_implicit_keep_alive_until_timeout(self, report):
        """Test whether the socket connection is kept alive by default and closed after the set timeout"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)
        self.check_connection_alive(report)
        time.sleep(self.LIFETIME_TIMEOUT + 1)
        report["notes"].append(f"Making a subsequent request after `{self.LIFETIME_TIMEOUT}` seconds")
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


    @HTTPTester.request("head-keep-alive-explicit.http", keep_alive=True, PATH="/a2-test/2/index.html")
    def test_explicit_keep_alive_until_timeout(self, report):
        """Test whether the socket connection is kept alive when explicitly requested and closed after the set timeout"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_payload_empty(report)
        self.check_connection_alive(report)
        time.sleep(self.LIFETIME_TIMEOUT + 1)
        report["notes"].append(f"Making a subsequent request after `{self.LIFETIME_TIMEOUT}` seconds")
        report2 = self.netcat("head-keep-alive-explicit.http", PATH="/a2-test/2/index.html")
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


    @HTTPTester.request("trace-many-conditionals.http", PATH="/a2-test/2/index.html")
    def test_trace_unnecessary_conditionals(self, report):
        """Test whether many unnecessary conditionals are not processed"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "message/http")
        self.check_payload_begins(report, "TRACE /a2-test/2/index.html HTTP/1.1")


    @HTTPTester.request("pipeline.http", PATH="/a2-test/", SUFFIX="2/index.html")
    def test_pipeline_requests(self, report):
        """Test whether multiple pipelined requests are processed and returned in the same order"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        orig_hdr = report["res"]["raw_headers"]
        try:
            report["notes"].append("Parsing second response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Second response should be a valid HTTP Message"
            self.check_status_is(report, 200)
            self.check_mime_is(report, "text/html")
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
            report["notes"].append("Parsing third response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Third response should be a valid HTTP Message"
            self.check_status_is(report, 200)
            self.check_mime_is(report, "text/html")
            self.check_payload_contains(report, "coolcar.html", "ford")
            self.check_connection_closed(report)
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
        except AssertionError:
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
            report["res"]["raw_headers"] = orig_hdr
            raise
        report["res"]["raw_headers"] = orig_hdr


    @HTTPTester.request("head-keep-alive.http", keep_alive=True, PATH="/a2-test/")
    def test_long_lived_connection(self, report):
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
            self.check_payload_contains(report3, "coolcar.html", "ford")
            self.check_connection_closed(report3)
            report["notes"] += report3["notes"]
        except AssertionError:
            report["errors"] = report3["errors"]
            report["notes"] += report3["notes"]
            raise
