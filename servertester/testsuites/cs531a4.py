import os
import hashlib

from ..base.httptester import HTTPTester


class CS531A4(HTTPTester):
    """CS531A4 is a special purpose HTTPTester with test cases for Assignment 4 of the CS531 (Web Server Design) course"""

    def __init__(self, hostport="localhost:80"):
        super().__init__(hostport=hostport)
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "messages", "cs531")
        self.USERAGENT = f"CS531 Assignment 4 Tester/{self.EPOCH}"


    # A helper method to be used in testing Digest authentication
    def generate_digest_values(self, nonce):
        cnonce = hashlib.md5(b"go hokies").hexdigest()
        ncount1 = "00000001"
        ncount2 = "00000002"
        a1 = hashlib.md5("mln:Colonial Place:mln".encode()).hexdigest()
        a2 = hashlib.md5(f"GET:http://{self.hostport}/a4-test/limited2/foo/bar.txt".encode()).hexdigest()
        a2_rspauth = hashlib.md5(f":http://{self.hostport}/a4-test/limited2/foo/bar.txt".encode()).hexdigest()
        response1 = hashlib.md5(f"{a1}:{nonce}:{ncount1}:{cnonce}:auth:{a2}".encode()).hexdigest()
        response2 = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2}".encode()).hexdigest()
        rspauth = hashlib.md5(f"{a1}:{nonce}:{ncount1}:{cnonce}:auth:{a2_rspauth}".encode()).hexdigest()
        return {"cnonce": cnonce, "nc1": ncount1, "nc2": ncount2, "resp1": response1, "resp2": response2, "rspauth": rspauth}


    @HTTPTester.request("get-url-ua.http", PATH="/a4-test/limited1/protected")
    def test_basic_auth_realm(self, report):
        """Test whether files are protected with HTTP Basic auth and return configured realm"""
        self.check_status_is(report, 401)
        self.check_header_is(report, "WWW-Authenticate", 'Basic realm="Fried Twice"')


    @HTTPTester.request("get-url-auth-ua.http", PATH="/a4-test/limited1/protected", AUTH="Basic YmRhOm1sbg==")
    def test_basic_wrong_auth_unauthorized(self, report):
        """Test whether access is unauthorized with wrong Authorization header"""
        self.check_status_is(report, 401)
        self.check_header_is(report, "WWW-Authenticate", 'Basic realm="Fried Twice"')


    @HTTPTester.request("get-url-ua.http", PATH="/a4-test/limited1/1/protected2")
    def test_nested_basic_auth(self, report):
        """Test whether files in nested directories are protected with HTTP Basic auth"""
        self.check_status_is(report, 401)
        self.check_header_is(report, "WWW-Authenticate", 'Basic realm="Fried Twice"')


    @HTTPTester.request("get-url-ref-auth.http", PATH="/a4-test/limited1/protected", REFERER="/a4-test/index.html", AUTH="Basic bWxuOm1sbg==")
    def test_basic_auth_ok(self, report):
        """Test whether access is granted with valid Authorization header"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "application/octet-stream")
        self.check_header_is(report, "Content-Length", "24")
        self.check_payload_contains(report, "this file is protected")


    @HTTPTester.request("get-url-auth-ua.http", PATH="/a4-test/limited1/1/protected2", AUTH="Basic YmRhOmJkYQ==")
    def test_nested_basic_auth_ok(self, report):
        """Test whether access is granted with valid Authorization header in nested directories"""
        self.check_status_is(report, 200)
        self.check_mime_is(report, "application/octet-stream")
        self.check_header_is(report, "Content-Length", "29")
        self.check_payload_contains(report, "this file is protected too!")


    @HTTPTester.request("get-url-bad-auth.http", PATH="/a4-test/limited1/protected", AUTH1="Basic YmRhOmJkYQ==", AUTH2="Basic ZZRhOmJkYQ==")
    def test_double_auth_bad(self, report):
        """Test whether two Authorization headers report a bad request"""
        self.check_status_is(report, 400)
        self.check_mime_is(report, "text/html")
        self.check_header_is(report, "Transfer-Encoding", "chunked")
        self.check_payload_not_empty(report)


    @HTTPTester.request("get-url-ua.http", PATH="/a4-test/limited2/foo/bar.txt")
    def test_nested_digest_auth(self, report):
        """Test whether files in nested directories are protected with HTTP Digest auth"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")


    @HTTPTester.request("method-url-ua.http", METHOD="HEAD", PATH="/a4-test/limited2/foo/bar.txt")
    def test_head_nested_digest_auth(self, report):
        """Test whether HEAD method in nested directories is protected with HTTP Digest auth"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")


    @HTTPTester.request("method-url-ua.http", METHOD="OPTIONS", PATH="/a4-test/limited2/foo/bar.txt")
    def test_options_nested_digest_auth(self, report):
        """Test whether OPTIONS method in nested directories is protected with HTTP Digest auth"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")


    @HTTPTester.request("get-url-ua.http", PATH="/a4-test/limited2/foo/bar.txt")
    def test_wrong_realm_unauthorized(self, report):
        """Test whether an incorrect realm prevents authorization"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        authstr = report["res"]["headers"].get("www-authenticate", "")
        authobj = self.parse_equal_sign_delimited_keys_values(authstr)
        report["notes"].append(f'`WWW-Authenticate` parsed for reuse in the `Authorization` header in the subsequent request')
        nonce = authobj.get("nonce", "")
        digval = self.generate_digest_values(nonce)
        report2 = self.netcat("get-url-auth-digest.http", PATH="/a4-test/limited2/foo/bar.txt", USER="mln", REALM="ColonialPlace", NONCE=nonce, NC=digval["nc1"], CNONCE=digval["cnonce"], RESPONSE=digval["resp1"])
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")


    @HTTPTester.request("get-url-ua.http", PATH="/a4-test/limited2/foo/bar.txt")
    def test_wrong_ncount_unauthorized(self, report):
        """Test whether an incorrect nonce count prevents authorization"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        authstr = report["res"]["headers"].get("www-authenticate", "")
        authobj = self.parse_equal_sign_delimited_keys_values(authstr)
        report["notes"].append(f'`WWW-Authenticate` parsed for reuse in the `Authorization` header in the subsequent request')
        nonce = authobj.get("nonce", "")
        digval = self.generate_digest_values(nonce)
        report2 = self.netcat("get-url-auth-digest.http", PATH="/a4-test/limited2/foo/bar.txt", USER="mln", REALM="Colonial Place", NONCE=nonce, NC=digval["nc2"], CNONCE=digval["cnonce"], RESPONSE=digval["resp1"])
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")


    @HTTPTester.request("get-url-ua.http", PATH="/a4-test/limited2/foo/bar.txt")
    def test_wrong_digest_response_unauthorized(self, report):
        """Test whether an incorrect digest response prevents authorization"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        authstr = report["res"]["headers"].get("www-authenticate", "")
        authobj = self.parse_equal_sign_delimited_keys_values(authstr)
        report["notes"].append(f'`WWW-Authenticate` parsed for reuse in the `Authorization` header in the subsequent request')
        nonce = authobj.get("nonce", "")
        digval = self.generate_digest_values(nonce)
        report2 = self.netcat("get-url-auth-digest.http", PATH="/a4-test/limited2/foo/bar.txt", USER="mln", REALM="Colonial Place", NONCE=nonce, NC=digval["nc1"], CNONCE=digval["cnonce"], RESPONSE=digval["resp2"])
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")


    @HTTPTester.request("get-url-ua.http", PATH="/a4-test/limited2/foo/bar.txt")
    def test_wrong_digest_user_unauthorized(self, report):
        """Test whether an incorrect digest user prevents authorization"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        authstr = report["res"]["headers"].get("www-authenticate", "")
        authobj = self.parse_equal_sign_delimited_keys_values(authstr)
        report["notes"].append(f'`WWW-Authenticate` parsed for reuse in the `Authorization` header in the subsequent request')
        nonce = authobj.get("nonce", "")
        digval = self.generate_digest_values(nonce)
        report2 = self.netcat("get-url-auth-digest.http", PATH="/a4-test/limited2/foo/bar.txt", USER="bda", REALM="Colonial Place", NONCE=nonce, NC=digval["nc2"], CNONCE=digval["cnonce"], RESPONSE=digval["resp2"])
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")


    @HTTPTester.request("get-url-ua.http", PATH="/a4-test/limited2/foo/bar.txt")
    def test_correct_realm_authorized(self, report):
        """Test whether a correct realm with other values grants authorization"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")
        authstr = report["res"]["headers"].get("www-authenticate", "")
        authobj = self.parse_equal_sign_delimited_keys_values(authstr)
        report["notes"].append(f'`WWW-Authenticate` parsed for reuse in the `Authorization` header in the subsequent request')
        nonce = authobj.get("nonce", "")
        digval = self.generate_digest_values(nonce)
        report2 = self.netcat("get-url-auth-digest.http", PATH="/a4-test/limited2/foo/bar.txt", USER="mln", REALM="Colonial Place", NONCE=nonce, NC=digval["nc1"], CNONCE=digval["cnonce"], RESPONSE=digval["resp1"])
        for k in report2:
            report[k] = report2[k]
        if report["errors"]:
            return
        self.check_status_is(report, 200)
        self.check_header_contains(report, "Authentication-Info", digval["rspauth"])


    @HTTPTester.request("get-if-match.http", PATH="/a4-test/limited2/foo/bar.txt", ETAG="x248kjaldsf00000000002")
    def test_auth_over_conditional_get(self, report):
        """Test whether authorization is ensured before conditional GET precondition check"""
        self.check_status_is(report, 401)
        self.check_header_begins(report, "WWW-Authenticate", "Digest")


    @HTTPTester.request("method-path-range.http", METHOD="HEAD", PATH="/a4-test/index.html.ru.koi8-r", RANGE="bytes=20000-29999")
    def test_large_range_not_satisfiable(self, report):
        """Test whether a Range larger than the file returns 416 Range Not Satisfiable"""
        self.check_status_is(report, 416)
        self.check_payload_empty(report)


    @HTTPTester.request("pipeline-auth.http", PATH1="/a4-test/limited1/protected", PATH2="/a4-test/index.html.de", PATH3="/a4-test/index.html.en", PATH4="/a4-test/index.html.ja.jis", RANGE="bytes=20000-29999", AUTH1="Basic YmRhOmJkYQ==", AUTH2="Basic YmRhOmJkYQxx")
    def test_pipeline_auth(self, report):
        """Test whether authorization is respected in pipeline requests"""
        self.check_status_is(report, 416)
        orig_hdr = report["res"]["raw_headers"]
        try:
            report["notes"].append("Parsing second response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Second response should be a valid HTTP Message"
            self.check_status_is(report, 200)
            self.check_mime_is(report, "text/html")
            self.check_header_is(report, "Content-Language", "de")
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
            report["notes"].append("Parsing third response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Third response should be a valid HTTP Message"
            self.check_status_is(report, 401)
            self.check_header_is(report, "WWW-Authenticate", 'Basic realm="Fried Twice"')
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
            report["notes"].append("Parsing fourth response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Fourth response should be a valid HTTP Message"
            self.check_status_is(report, 200)
            self.check_mime_is(report, "text/html")
            self.check_header_is(report, "Content-Language", "en")
            orig_hdr += "\r\n\r\n" + report["res"]["raw_headers"]
            report["notes"].append("Parsing fifth response")
            self.parse_response(report["res"]["payload"], report)
            assert not report["errors"], "Fifth response should be a valid HTTP Message"
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
