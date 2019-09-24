import os

from ..base.httptester import HTTPTester


class Echo(HTTPTester):
    """Echo HTTPTester contains various test cases to evaluate an echo server"""


    def __init__(self, hostport="localhost:80"):
        super().__init__(hostport=hostport)
        self.MSGDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "messages", "echo")
        self.USERAGENT = f"Echo Back Tester/{self.EPOCH}"


    @HTTPTester.request("single-line.txt", skip_parsing=True)
    def test_echo_back_single_line(self, report):
        """Test echo back server with a single line message"""
        line = report["req"]["raw"].strip()
        assert line in report["res"]["raw_headers"], f"`{line}` is absent from the response"
        report["notes"].append(f"`{line}` is present in the response")


    @HTTPTester.request("multi-line.txt", skip_parsing=True)
    def test_echo_back_multi_line(self, report):
        """Test echo back server with a multi line message"""
        for line in report["req"]["raw"].strip().splitlines():
            assert line in report["res"]["raw_headers"], f"`{line}` is absent from the response"
            report["notes"].append(f"`{line}` is present in the response")


    @HTTPTester.request("sparse-line.txt", skip_parsing=True)
    def test_echo_back_sparse_line(self, report):
        """Test echo back server with a message containing some empty lines"""
        for line in filter(None, [l.strip() for l in report["req"]["raw"].strip().splitlines()]):
            assert line in report["res"]["raw_headers"], f"`{line}` is absent from the response"
            report["notes"].append(f"`{line}` is present in the response")
