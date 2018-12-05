import time

from ..base.httptester import HTTPTester


class CS531A4(HTTPTester):
    """CS531A4 is a special purpose HTTPTester with test cases for Assignment 4 of the CS531 (Web Server Design) course"""

    @HTTPTester.request("get-root.http")
    def test_1(self, report):
        """Placeholder test case 1"""
        self.check_status_is(report, 200)
