import os

from ..base.httptester import HTTPTester


class Example(HTTPTester):
    """Example HTTPTester contains some sample test cases"""


    def __init__(self, hostport="localhost:80"):
        super().__init__(hostport=hostport)
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "messages", "example")
        self.USERAGENT = f"Example Tester/{self.EPOCH}"


    @HTTPTester.request("get-root.http")
    def test_healthy_server(self, report):
        """Test healthy server root"""
        self.check_status_is(report, 200)
        self.check_date_valid(report)
        self.check_header_present(report, "Content-Type")
        self.check_version_is(report, "HTTP/1.1")


    @HTTPTester.request("malformed-header.http")
    def test_bad_request_header(self, report):
        """Test whether the server recognizes malformed headers"""
        self.check_status_is(report, 400)


    @HTTPTester.request("get-root.http")
    def test_the_ultimate_question(self, report):
        """Answer to the Ultimate Question of Life, the Universe, and Everything"""
        assert False, "A placeholder test, meant to always fail!"
