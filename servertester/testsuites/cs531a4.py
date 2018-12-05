from ..base.httptester import HTTPTester


class CS531A4(HTTPTester):
    """CS531A4 is a special purpose HTTPTester with test cases for Assignment 4 of the CS531 (Web Server Design) course"""

    @HTTPTester.request("get-root.http")
    def test_1(self, report):
        """Test case 1"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_2(self, report):
        """Test case 2"""
        self.check_status_is(report, 200)


    @HTTPTester.request("get-root.http")
    def test_3(self, report):
        """Test case 3"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_4(self, report):
        """Test case 4"""
        self.check_status_is(report, 200)


    @HTTPTester.request("get-root.http")
    def test_5(self, report):
        """Test case 5"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_6(self, report):
        """Test case 6"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_7(self, report):
        """Test case 7"""
        self.check_status_is(report, 200)


    @HTTPTester.request("get-root.http")
    def test_8(self, report):
        """Test case 8"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_9(self, report):
        """Test case 9"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_10(self, report):
        """Test case 10"""
        self.check_status_is(report, 200)


    @HTTPTester.request("get-root.http")
    def test_11(self, report):
        """Test case 11"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_12(self, report):
        """Test case 12"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_13(self, report):
        """Test case 13"""
        self.check_status_is(report, 400)


    @HTTPTester.request("get-root.http")
    def test_14(self, report):
        """Test case 14"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_15(self, report):
        """Test case 15"""
        self.check_status_is(report, 401)


    @HTTPTester.request("get-root.http")
    def test_16(self, report):
        """Test case 16"""
        self.check_status_is(report, 416)


    @HTTPTester.request("get-root.http")
    def test_17(self, report):
        """Test case 17"""
        self.check_status_is(report, 416)
