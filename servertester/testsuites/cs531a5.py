import os
import hashlib

from ..base.httptester import HTTPTester


class CS531A5(HTTPTester):
    """CS531A5 is a special purpose HTTPTester with test cases for Assignment 5 of the CS531 (Web Server Design) course"""

    def __init__(self, hostport="localhost:80"):
        super().__init__(hostport=hostport)
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "messages", "cs531")
        self.USERAGENT = f"CS531 Assignment 5 Tester/{self.EPOCH}"


    # A helper method to be used in testing Digest authentication
    def generate_digest_values(self, nonce):
        cnonce = hashlib.md5(b"go hokies").hexdigest()
        ncount1 = "00000001"
        ncount2 = "00000002"
        a1 = hashlib.md5("bda:Colonial Place:bda".encode()).hexdigest()
        a2 = hashlib.md5(f"PUT:http://{self.hostport}/a5-test/limited4/foo/barbar.txt".encode()).hexdigest()
        a2_get = hashlib.md5(f"GET:http://{self.hostport}/a5-test/limited4/foo/barbar.txt".encode()).hexdigest()
        a2_delete = hashlib.md5(f"DELETE:http://{self.hostport}/a5-test/limited4/foo/barbar.txt".encode()).hexdigest()
        a2_rspauth = hashlib.md5(f":http://{self.hostport}/a5-test/limited4/foo/barbar.txt".encode()).hexdigest()
        response1 = hashlib.md5(f"{a1}:{nonce}:{ncount1}:{cnonce}:auth:{a2}".encode()).hexdigest()
        response2 = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2}".encode()).hexdigest()
        response2_get = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2_get}".encode()).hexdigest()
        rspauth2 = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2_rspauth}".encode()).hexdigest()
        response3_get = hashlib.md5(f"{a1}:{nonce}:{ncount1}:{cnonce}:auth:{a2_get}".encode()).hexdigest()
        rspauth3 = hashlib.md5(f"{a1}:{nonce}:{ncount1}:{cnonce}:auth:{a2_rspauth}".encode()).hexdigest()
        response4_delete = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2_delete}".encode()).hexdigest()
        rspauth4 = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2_rspauth}".encode()).hexdigest()
        return {"cnonce": cnonce, "nc1": ncount1, "nc2": ncount2, "resp1": response1, "resp2": response2, "resp2g": response2_get, "resp3g": response3_get, "resp4d": response4_delete, "rspauth2": rspauth2, "rspauth3": rspauth3, "rspauth4": rspauth4}


    def process_next_response(self, report, postion="Next"):
        pld, rest = self.slice_payload(report["res"]["payload"], report)
        report["orig_hdr"] += report["res"]["raw_headers"] + "\r\n\r\n" + pld.decode()
        assert not report["errors"], "Failed to extract payload"
        report["notes"].append(f"Parsing {postion.lower()} response")
        self.parse_response(rest, report)
        assert not report["errors"], f"{postion} response should be a valid HTTP Message"


    @HTTPTester.request("pipeline-oto.http", PATH1="/a5-test/limited3/protected", PATH2="/a5-test/env.cgi?var1=foo&var2=bar", PATH3="/a5-test/limited3/env.cgi", REFERER="/a5-test/index.html", AUTH="Basic amJvbGxlbjpqYm9sbGVu")
    def test_protected_options_trace_full_method_support(self, report):
        """Test whether OPTIONS and TRACE methods are auth protected and return full HTTP method support"""
        self.check_status_is(report, 401)
        self.check_header_is(report, "WWW-Authenticate", 'Basic realm="Fried Twice"')
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        report["orig_hdr"] = ""
        try:
            self.process_next_response(report, "Second")
            self.check_status_is(report, 200)
            self.check_mime_is(report, "message/http")
            self.check_payload_contains(report, "TRACE /a5-test/env.cgi?var1=foo&var2=bar HTTP/1.1")
            self.process_next_response(report, "Third")
            self.check_status_is(report, 200)
            self.check_header_contains(report, "Allow", "GET", "HEAD", "OPTIONS", "TRACE", "POST", "PUT", "DELETE")
            self.check_connection_closed(report)
            report["orig_hdr"] += report["res"]["raw_headers"]
        except AssertionError:
            report["orig_hdr"] += report["res"]["raw_headers"]
            report["res"]["raw_headers"] = report["orig_hdr"]
            raise
        report["res"]["raw_headers"] = report["orig_hdr"]


    @HTTPTester.request("pipeline-ggg.http", PATH1="/a5-test/status.cgi", PATH2="/a5-test/ls.cgi", PATH3="/a5-test/location.cgi")
    def test_multiple_cgi_scripts(self, report):
        """Test whether CGI scripts are executed and resulted in custom status, directory listing, and redirection"""
        self.check_status_is(report, 678)
        self.check_payload_doesnt_begin(report, "#!/usr/bin/perl")
        report["orig_hdr"] = ""
        try:
            self.process_next_response(report, "Second")
            self.check_status_is(report, 200)
            self.check_mime_is(report, "text/plain")
            self.check_header_is(report, "Transfer-Encoding", "chunked")
            self.check_header_absent(report, "ETag")
            self.check_payload_doesnt_begin(report, "#!/usr/bin/perl")
            self.check_payload_contains(report, "drwxr-xr-x", "limited4/foo", "WeMustProtectThisHouse!")
            self.process_next_response(report, "Third")
            self.check_status_is(report, 302)
            self.check_mime_is(report, "text/html")
            self.check_header_is(report, "Transfer-Encoding", "chunked")
            self.check_header_is(report, "Location", "http://www.cs.odu.edu/~mln/")
            self.check_payload_doesnt_begin(report, "#!/usr/bin/perl")
            self.check_connection_closed(report)
            report["orig_hdr"] += report["res"]["raw_headers"]
        except AssertionError:
            report["orig_hdr"] += report["res"]["raw_headers"]
            report["res"]["raw_headers"] = report["orig_hdr"]
            raise
        report["res"]["raw_headers"] = report["orig_hdr"]


    @HTTPTester.request("pipeline-gg.http", PATH1="/a5-test/limited4/foo/barbar.txt", PATH2="/a5-test/500.cgi")
    def test_cgi_auth_internal_error(self, report):
        """Test whether CGI scripts are protected and return 500 Internal Server Error on malformed output"""
        self.check_status_is(report, 401)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        report["orig_hdr"] = ""
        try:
            self.process_next_response(report, "Second")
            self.check_status_is(report, 500)
            self.check_mime_is(report, "text/html")
            self.check_header_is(report, "Transfer-Encoding", "chunked")
            self.check_payload_doesnt_begin(report, "#!/usr/bin/perl")
            self.check_payload_doesnt_contain(report, "drwxr-xr-x")
            report["orig_hdr"] += report["res"]["raw_headers"]
        except AssertionError:
            report["orig_hdr"] += report["res"]["raw_headers"]
            report["res"]["raw_headers"] = report["orig_hdr"]
            raise
        report["res"]["raw_headers"] = report["orig_hdr"]


    @HTTPTester.request("method-url-ua.http", METHOD="OPTIONS", PATH="/a5-test/env.cgi")
    def test_allow_no_put_delete(self, report):
        """Test whether Allow header is present with values other than PUT and DELETE"""
        self.check_status_is(report, 200)
        self.check_header_contains(report, "Allow", "GET", "HEAD", "OPTIONS", "TRACE", "POST")
        self.check_header_doesnt_contain(report, "Allow", "PUT", "DELETE")


    @HTTPTester.request("method-path.http", METHOD="DELETE", PATH="/a5-test/index.html.denmark")
    def test_delete_not_allowed(self, report):
        """Test whether Allow header is present with appropriate values other than DELETE in the 405 Not Allowed response"""
        self.check_status_is(report, 405)
        self.check_header_contains(report, "Allow", "GET", "HEAD", "OPTIONS", "TRACE")
        self.check_header_doesnt_contain(report, "Allow", "DELETE")


    @HTTPTester.request("put-url-auth-basic.http", PATH="/a5-test/limited1/foobar.txt", AUTH="Basic YmRhOmJkYQ==")
    def test_put_not_allowed(self, report):
        """Test whether Allow header is present with appropriate values other than PUT in the 405 Not Allowed response"""
        self.check_status_is(report, 405)
        self.check_header_contains(report, "Allow", "GET", "HEAD", "OPTIONS", "TRACE", "DELETE")
        self.check_header_doesnt_contain(report, "Allow", "PUT")


    @HTTPTester.request("get-url.http", PATH="/a5-test/limited4/foo/barbar.txt")
    def test_put_success_auth_digest(self, report):
        """Test whether PUT method creates a new resource with the request payload after successful Digest auth"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        authstr = report["res"]["headers"].get("www-authenticate", "")
        authobj = self.parse_equal_sign_delimited_keys_values(authstr)
        report["notes"].append(f'`WWW-Authenticate` parsed for reuse in the `Authorization` header in the subsequent request')
        nonce = authobj.get("nonce", "")
        digval = self.generate_digest_values(nonce)
        report2 = self.netcat("put-url-auth-digest.http", PATH="/a5-test/limited4/foo/barbar.txt", USER="bda", REALM="Colonial Place", NONCE=nonce, NC=digval["nc1"], CNONCE=digval["cnonce"], RESPONSE=digval["resp1"])
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 201)
        self.check_header_contains(report, "Authentication-Info", digval["rspauth3"])


    @HTTPTester.request("put-url-auth-basic.http", PATH="/a5-test/limited3/foobar.txt", AUTH="Basic YmRhOmJkYQ==")
    def test_put_success_auth_basic(self, report):
        """Test whether PUT method creates a new resource with the request payload after successful Basic auth"""
        self.check_status_is(report, 201)


    @HTTPTester.request("get-url.http", PATH="/a5-test/limited4/foo/barbar.txt")
    def test_auth_created_files(self, report):
        """Test whether files created using PUT in earlier tests are auth protected properly"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        authstr = report["res"]["headers"].get("www-authenticate", "")
        authobj = self.parse_equal_sign_delimited_keys_values(authstr)
        report["notes"].append(f'`WWW-Authenticate` parsed for reuse in the `Authorization` header in the subsequent request')
        nonce = authobj.get("nonce", "")
        digval = self.generate_digest_values(nonce)
        report2 = self.netcat("pipeline-auth-bd.http", PATH1="/a5-test/limited3/foobar.txt", PATH2="/a5-test/limited4/foo/barbar.txt", AUTH="Basic YmRhOmJkYQ==", USER="bda", REALM="Colonial Place", NONCE=nonce, NC=digval["nc2"], CNONCE=digval["cnonce"], RESPONSE=digval["resp2g"])
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 200)
        self.check_etag_valid(report)
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "63")
        self.check_payload_contains(report, "here comes a PUT method", "hooray for PUT!")
        report["orig_hdr"] = ""
        try:
            self.process_next_response(report, "Second")
            self.check_status_is(report, 401)
            self.check_mime_is(report, "text/html")
            self.check_header_is(report, "Transfer-Encoding", "chunked")
            self.check_header_begins(report, "WWW-Authenticate", "Digest")
            report["orig_hdr"] += report["res"]["raw_headers"]
        except AssertionError:
            report["orig_hdr"] += report["res"]["raw_headers"]
            report["res"]["raw_headers"] = report["orig_hdr"]
            raise
        report["res"]["raw_headers"] = report["orig_hdr"]


    @HTTPTester.request("pipeline-auth-dg.http", PATH="/a5-test/limited3/foobar.txt", AUTH="Basic YmRhOmJkYQ==")
    def test_delete_verify(self, report):
        """Test whether a DELETE request removes a resource and returns 404 on a subsequent GET"""
        self.check_status_is(report, 200)
        report["orig_hdr"] = ""
        try:
            self.process_next_response(report, "Second")
            self.check_status_is(report, 404)
            self.check_mime_is(report, "text/html")
            self.check_header_is(report, "Transfer-Encoding", "chunked")
            self.check_payload_not_empty(report)
            self.check_payload_doesnt_contain(report, "here comes a PUT method")
            report["orig_hdr"] += report["res"]["raw_headers"]
        except AssertionError:
            report["orig_hdr"] += report["res"]["raw_headers"]
            report["res"]["raw_headers"] = report["orig_hdr"]
            raise
        report["res"]["raw_headers"] = report["orig_hdr"]


    @HTTPTester.request("pipeline-auth-pg.http", PATH1="/a5-test/limited2/test.txt", PATH2="/a5-test/limited3/foobar.txt", AUTH1="Basic YmRhOmJkYQ==", AUTH2="Basic alsdkfjlasjd")
    def test_pipeline_auth_put_get(self, report):
        """Test whether pipelined PUT and GET requests are auth protected (Note: some request headers maight be separated by LF instead of CRLF)"""
        self.check_status_is(report, 401)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        report["orig_hdr"] = ""
        try:
            self.process_next_response(report, "Second")
            self.check_status_is(report, 401)
            self.check_mime_is(report, "text/html")
            self.check_header_is(report, "Transfer-Encoding", "chunked")
            self.check_header_is(report, "WWW-Authenticate", 'Basic realm="Fried Twice"')
            report["orig_hdr"] += report["res"]["raw_headers"]
        except AssertionError:
            report["orig_hdr"] += report["res"]["raw_headers"]
            report["res"]["raw_headers"] = report["orig_hdr"]
            raise
        report["res"]["raw_headers"] = report["orig_hdr"]


    @HTTPTester.request("get-url.http", PATH="/a5-test/limited4/foo/barbar.txt")
    def test_auth_get_delete(self, report):
        """Test whether a file that was PUT in an earlier test is auth protected, returns 200 OK on GET, and can be deleted successfully"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        authstr = report["res"]["headers"].get("www-authenticate", "")
        authobj = self.parse_equal_sign_delimited_keys_values(authstr)
        report["notes"].append(f'`WWW-Authenticate` parsed for reuse in the `Authorization` header in the subsequent request')
        nonce = authobj.get("nonce", "")
        digval = self.generate_digest_values(nonce)
        report2 = self.netcat("pipeline-auth-gd.http", PATH="/a5-test/limited4/foo/barbar.txt", USER="bda", REALM="Colonial Place", NONCE=nonce, NC1=digval["nc1"], NC2=digval["nc2"], CNONCE=digval["cnonce"], RESPONSE1=digval["resp3g"], RESPONSE2=digval["resp4d"])
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 200)
        self.check_etag_valid(report)
        self.check_header_contains(report, "Authentication-Info", digval["rspauth3"])
        self.check_mime_is(report, "text/plain")
        self.check_header_is(report, "Content-Length", "65")
        self.check_payload_contains(report, "here comes a PUT method", "hooray for PUT!!!")
        report["orig_hdr"] = ""
        try:
            self.process_next_response(report, "Second")
            self.check_status_is(report, 200)
            self.check_header_contains(report, "Authentication-Info", digval["rspauth4"])
            report["orig_hdr"] += report["res"]["raw_headers"]
        except AssertionError:
            report["orig_hdr"] += report["res"]["raw_headers"]
            report["res"]["raw_headers"] = report["orig_hdr"]
            raise
        report["res"]["raw_headers"] = report["orig_hdr"]


    @HTTPTester.request("get-path-ua.http", PATH="/a5-test/env.cgi?var1=foo&var2=bar")
    def test_cgi_env_query_str(self, report):
        """Test whether CGI script can see and report environment variables like QUERY_STRING and HTTP_USER_AGENT"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_header_absent(report, "ETag")
        self.check_payload_contains(report, "QUERY_STRING = var1=foo&var2=bar", f"HTTP_USER_AGENT = {self.USERAGENT}")


    @HTTPTester.request("get-path.http", PATH="/a5-test/limited3/env.cgi?var1=foo&var2=bar")
    def test_cgi_protected_auth_basic(self, report):
        """Test whether CGI script is protected with HTTP Basic auth"""
        self.check_status_is(report, 401)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_header_is(report, "WWW-Authenticate", 'Basic realm="Fried Twice"')


    @HTTPTester.request("post-path-www-urlencoded.http", PATH="/a5-test/limited3/env.cgi", AUTH="Basic YmRhOmJkYQ==")
    def test_post_www_urlencoded(self, report):
        """Test whether CGI script reads and echoes back URL-encoded POST data"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_header_absent(report, "ETag")
        self.check_payload_contains(report, "REQUEST_METHOD = POST", "REMOTE_USER = bda", "var1=foo&var2=bar")


    @HTTPTester.request("post-path-multipart.http", PATH="/a5-test/limited3/env.cgi", AUTH="Basic YmRhOmJkYQ==")
    def test_post_www_multipart(self, report):
        """Test whether CGI script reads and echoes back multipart POST data"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_header_absent(report, "ETag")
        self.check_payload_contains(report, "REQUEST_METHOD = POST", "REMOTE_USER = bda", "userinput", "test 1 2 3", "domain", "cs.odu.edu")
