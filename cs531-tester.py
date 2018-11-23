import time


class CS531Tester(WebServerTester):
    """CS531Tester is a special purpose WebServerTester with test cases for CS531 (Web Server Design) course"""


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
        report["notes"].append(f'`ETag` fetched for reuse as `"{etag}"` in the subsequent request')
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
            self.check_payload_contains(report, "coolcar.html")
            self.check_payload_contains(report, "ford")
            self.check_connection_closed(report)
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
        except AssertionError:
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
            report["res"]["raw_headers"] = orig_hdr
            raise
        report["res"]["raw_headers"] = orig_hdr


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


    @make_request("get-url-ua.http", PATH="/a3-test/fairlane.txt", USERAGENT="CS 431/531 A3 Automated Checker")
    def test_3_useragent_get_text_ok(self, report):
        """Test whether a request with a custom user-agent returns OK with corresponding text response"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "193")
        self.check_payload_contains(report, "______________")


    @make_request("get-url-range-referer.http", PATH="/a3-test/index.html", SUFFIX=".es", RANGE="bytes=0-99", USERAGENT="CS 431/531 A3 Automated Checker")
    def test_3_partial_content_range_language(self, report):
        """Test whether a valid range request header returns partial content in a specific langaue"""
        self.check_status_is(report, 206)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Content-Language", "es")
        self.check_header_present(report, "Content-Range")
        self.check_header_is(report, "Content-Length", "100")
        self.check_payload_size(report, 100)


    @make_request("get-path-ua.http", PATH="/a3-test/index.htmll", USERAGENT="CS 431/531 A3 Automated Checker")
    def test_3_chunked_404(self, report):
        """Test whether a 404 Not Found page returns chunked encoded HTML"""
        self.check_status_is(report, 404)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_not_empty(report)


    @make_request("conditional-head.http", PATH="/a3-test/fairlane.gif", MODTIME="Sat, 10 Nov 2018 20:46:11 GMT")
    def test_3_conditional_head_image_fresh(self, report):
        """Test whether conditional HEAD of a fresh image file returns 304 Not Modified"""
        self.check_status_is(report, 304)
        self.check_payload_empty(report)


    @make_request("conditional-head.http", PATH="/a3-test/fairlane.gif", MODTIME="Sat, 27 Oct 2018 20:46:09 GMT")
    def test_3_conditional_head_image_stale(self, report):
        """Test whether conditional HEAD of a stale image file returns 200 OK"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "image/gif")
        self.check_payload_empty(report)


    @make_request("head-path.http", PATH="/a3-test/fairlane")
    def test_3_no_accept_header_multiple_choices(self, report):
        """Test whether missing Accept header yields multiple choices"""
        self.check_status_is(report, 300)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_empty(report)


    @make_request("get-path-accept.http", PATH="/a3-test/fairlane", ACCEPT="image/*; q=1.0")
    def test_3_ambiguous_accept_header_multiple_choices(self, report):
        """Test whether an Accept header with the same qvalue for all image types yields multiple choices"""
        self.check_status_is(report, 300)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_not_empty(report)


    @make_request("head-path-accept.http", PATH="/a3-test/fairlane", ACCEPT="image/jpeg; q=0.9, image/png; q=0.91, image/tiff; q=0.95", USERAGENT="CS 431/531 A3 Automated Checker")
    def test_3_accept_header_png_ok(self, report):
        """Test whether an Accept header with unique qvalue returns a PNG"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "image/png")
        self.check_header_is(report, "Content-Length", "98203")
        self.check_payload_empty(report)


    @make_request("head-path-accept.http", PATH="/a3-test/fairlane", ACCEPT="text/*; q=1.0, image/*; q=0.99", USERAGENT="CS 431/531 A3 Automated Checker")
    def test_3_accept_header_text_ok(self, report):
        """Test whether an Accept header with high qvalue returns plain text"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "193")
        self.check_payload_empty(report)


    @make_request("head-path-accept-attr.http", PATH="/a3-test/vt-uva.html", ACCEPTATTR="Encoding", ACCEPTVAL="compress; q=0.0, gzip; q=0.0, deflate; q=0.5")
    def test_3_not_accptable_encoding(self, report):
        """Test whether explicit zero qvalue for all supported encodings returns 406 Not Acceptable"""
        self.check_status_is(report, 406)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_empty(report)


    @make_request("head-path-accept-attr.http", PATH="/a3-test/vt-uva.html.Z", ACCEPTATTR="Encoding", ACCEPTVAL="compress; q=0.0, gzip; q=0.5")
    def test_3_explicit_extention_ignore_content_negotiation(self, report):
        """Test whether an explicit existing file extension ignores contnet negotiation"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Content-Encoding", "compress")
        self.check_header_is(report, "Content-Length", "42757")
        self.check_payload_empty(report)


    @make_request("head-path-accept-attr.http", PATH="/a3-test/index.html", ACCEPTATTR="Language", ACCEPTVAL="en; q=1.0, de; q=1.0, fr; q=1.0")
    def test_3_ambiguous_accept_language_multiple_choices(self, report):
        """Test whether an Accept-Language header with the same qvalue for more than one available languages yields multiple choices"""
        self.check_status_is(report, 300)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_empty(report)


    @make_request("head-path-accept-language-charset.http", PATH="/a3-test/index.html.ja", LANGUAGE="en; q=1.0, ja; q=0.5", CHARSET="euc-jp; q=1.0, iso-2022-jp; q=0.0")
    def test_3_not_accptable_incompatiple_charset(self, report):
        """Test whether explicit zero qvalue of charset associated with the explicit language extension returns 406 Not Acceptable"""
        self.check_status_is(report, 406)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_empty(report)


    @make_request("get-path-range.http", PATH="/a3-test/fairlane.txt", RANGE="bytes=10-20")
    def test_3_partial_content_range_text(self, report):
        """Test whether a valid range request header returns partial content in plain text"""
        self.check_status_is(report, 206)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Range", "bytes 10-20/193")
        self.check_header_is(report, "Content-Length", "11")
        self.check_payload_size(report, 11)


    @make_request("get-if-match.http", PATH="/a3-test/fairlane.txt", ETAG="20933948kjaldsf000002")
    def test_3_etag_precondition_failure(self, report):
        """Test whether a random If-Match ETag returns 412 Precondition Failed"""
        self.check_status_is(report, 412)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_not_empty(report)


    @make_request("get-path-ua.http", PATH="/a3-test/index.html.ru.koi8-r", USERAGENT="CS 431/531 A3 Automated Checker")
    def test_3_explicit_language_charset_etag(self, report):
        """Test whether explicit language and charset as extensions returns ETag and Content-Type with charset"""
        self.check_status_is(report, 200)
        self.check_header_is(report, "Content-Type", "text/html; charset=koi8-r")
        self.check_header_is(report, "Content-Language", "ru")
        self.check_etag_valid(report)
        self.check_payload_size(report, 7277)


    @make_request("get-path-ua.http", PATH="/a3-test/index.html.ru.koi8-r", USERAGENT="CS 431/531 A3 Automated Checker")
    def test_3_valid_etag_conditional_get(self, report):
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


    @make_request("pipeline-range.http", PATH="/a3-test/index.html", SUFFIX1=".en", SUFFIX2=".ja.jis")
    def test_3_pipeline_range_negotiate(self, report):
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


    @make_request("get-root.http")
    def test_42_the_untimate_question(self, report):
        """Answer to the Ultimate Question of Life, the Universe, and Everything"""
        assert False, "A placeholder test, meant to always fail!"
