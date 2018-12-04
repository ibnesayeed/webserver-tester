import time

from ..base.httptester import HTTPTester


class Example(HTTPTester):
    """Example HTTPTester contains some sample test cases"""


    @HTTPTester.request("get-root.http")
    def test_0_healthy_server(self, report):
        """Test healthy server root"""
        self.check_status_is(report, 200)
        self.check_date_valid(report)
        self.check_header_present(report, "Content-Type")
        self.check_version_is(report, "HTTP/1.1")


    @HTTPTester.request("malformed-header.http")
    def test_0_bad_request_header(self, report):
        """Test whether the server recognizes malformed headers"""
        self.check_status_is(report, 400)


    @HTTPTester.request("get-root.http")
    def test_42_the_untimate_question(self, report):
        """Answer to the Ultimate Question of Life, the Universe, and Everything"""
        assert False, "A placeholder test, meant to always fail!"
