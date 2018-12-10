import hashlib

from ..base.httptester import HTTPTester


class CS531A5(HTTPTester):
    """CS531A5 is a special purpose HTTPTester with test cases for Assignment 5 of the CS531 (Web Server Design) course"""

    # A helper method to be used in testing Digest authentication
    def generate_digest_values(self, nonce):
        cnonce = hashlib.md5(b"go hokies").hexdigest()
        ncount1 = "00000001"
        ncount2 = "00000002"
        a1 = hashlib.md5("bda:Colonial Place:bda".encode()).hexdigest()
        a2 = hashlib.md5(f"PUT:http://{self.hostport}/a5-test/limited4/foo/barbar.txt".encode()).hexdigest()
        a2_get = hashlib.md5(f"GET:http://{self.hostport}/a5-test/limited4/foo/barbar.txt".encode()).hexdigest()
        a2_delete = hashlib.md5(f"DELETE:http://{self.hostport}/a5-test/limited4/foo/barbar.txt".encode()).hexdigest()
        a2_rspauth = hashlib.md5(f":http://{self.hostport}/a5-test/limited2/foo/bar.txt".encode()).hexdigest()
        response1 = hashlib.md5(f"{a1}:{nonce}:{ncount1}:{cnonce}:auth:{a2}".encode()).hexdigest()
        response2 = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2}".encode()).hexdigest()
        response2_get = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2_get}".encode()).hexdigest()
        rspauth2 = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2_rspauth}".encode()).hexdigest()
        response3_get = hashlib.md5(f"{a1}:{nonce}:{ncount1}:{cnonce}:auth:{a2_get}".encode()).hexdigest()
        rspauth3 = hashlib.md5(f"{a1}:{nonce}:{ncount1}:{cnonce}:auth:{a2_rspauth}".encode()).hexdigest()
        response4_delete = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2_delete}".encode()).hexdigest()
        rspauth4 = hashlib.md5(f"{a1}:{nonce}:{ncount2}:{cnonce}:auth:{a2_rspauth}".encode()).hexdigest()
        return {"cnonce": cnonce, "nc1": ncount1, "nc2": ncount2, "resp1": response1, "resp2": response2, "resp2g": response2_get, "resp3g": response3_get, "resp4d": response4_delete, "rspauth2": rspauth2, "rspauth3": rspauth3, "rspauth4": rspauth4}


    @HTTPTester.request("pipeline-oto.http", PATH1="/a5-test/limited3/protected", PATH2="/a5-test/env.cgi?var1=foo&var2=bar", PATH3="/a5-test/limited3/env.cgi", REFERER="/a5-test/index.html", AUTH="Basic amJvbGxlbjpqYm9sbGVu", USERAGENT="CS 531-F18 A5 automated Checker")
    def test_1(self, report):
        """TODO: Yet to implement!"""
        assert False, "Assertions not added yet!"


    @HTTPTester.request("pipeline-ggg.http", PATH1="/a5-test/status.cgi", PATH2="/a5-test/ls.cgi", PATH3="/a5-test/location.cgi")
    def test_2(self, report):
        """TODO: Yet to implement!"""
        assert False, "Assertions not added yet!"


    @HTTPTester.request("pipeline-gg.http", PATH1="/a5-test/limited4/foo/barbar.txt", PATH2="/a5-test/500.cgi")
    def test_3(self, report):
        """TODO: Yet to implement!"""
        assert False, "Assertions not added yet!"


    @HTTPTester.request("method-url-ua.http", METHOD="OPTIONS", PATH="/a5-test/env.cgi", USERAGENT="CS 531-F18 A5 automated Checker")
    def test_4(self, report):
        """TODO: Yet to implement!"""
        assert False, "Assertions not added yet!"


    @HTTPTester.request("method-path.http", METHOD="DELETE", PATH="/a5-test/index.html.denmark")
    def test_5(self, report):
        """TODO: Yet to implement!"""
        assert False, "Assertions not added yet!"


    @HTTPTester.request("put-url-auth-basic.http", PATH="/a5-test/limited1/foobar.txt", AUTH="Basic YmRhOmJkYQ==", USERAGENT="CS 531-F18 A5 automated Checker")
    def test_6(self, report):
        """TODO: Yet to implement!"""
        assert False, "Assertions not added yet!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/limited4/foo/barbar.txt")
    def test_7(self, report):
        """TODO: Yet to implement!"""
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
        assert False, "Assertions not added yet!"


    @HTTPTester.request("put-url-auth-basic.http", PATH="/a5-test/limited3/foobar.txt", AUTH="Basic YmRhOmJkYQ==", USERAGENT="CS 531-F18 A5 automated Checker")
    def test_8(self, report):
        """TODO: Yet to implement!"""
        assert False, "Assertions not added yet!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/")
    def test_9(self, report):
        """TODO: Yet to implement!"""
        assert False, "Yet to implement!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/")
    def test_10(self, report):
        """TODO: Yet to implement!"""
        assert False, "Yet to implement!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/")
    def test_11(self, report):
        """TODO: Yet to implement!"""
        assert False, "Yet to implement!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/")
    def test_12(self, report):
        """TODO: Yet to implement!"""
        assert False, "Yet to implement!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/")
    def test_13(self, report):
        """TODO: Yet to implement!"""
        assert False, "Yet to implement!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/")
    def test_14(self, report):
        """TODO: Yet to implement!"""
        assert False, "Yet to implement!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/")
    def test_15(self, report):
        """TODO: Yet to implement!"""
        assert False, "Yet to implement!"


    @HTTPTester.request("get-root.http", PATH="/a5-test/")
    def test_16(self, report):
        """TODO: Yet to implement!"""
        assert False, "Yet to implement!"
