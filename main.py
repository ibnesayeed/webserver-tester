#!/usr/bin/env python3

import sys
import re
import collections

from servertester.testsuites import *


if __name__ == "__main__":
    def print_help():
        print("")
        print("Usage:")
        print("./main.py [[<host>]:[<port>] [<test-id>|<assignment-numbers>]]")
        print("")
        print("<host>               : Hostname or IP address of the server to be tested (default: 'localhost')")
        print("<port>               : Port number of the server to be tested (default: '80')")
        print("<test-id>            : ID of an individual test function (e.g., 'test_0_healthy_server')")
        print("<assignment-numbers> : Comma separated list of assignment numbers (default: all assignments)")
        print("")

    def colorize(str, code=91):
        return f"\033[{code}m{str}\033[0m"

    if {"-h", "--help"}.intersection(sys.argv):
        print_help()
        sys.exit(0)

    suit = Example

    if len(sys.argv) < 2:
        print()
        print("Following test cases are available:")
        for suite in testsuites:
            print()
            print(f"{'=' * 10} Test Suite: {colorize(suite)} {'=' * 10}")
            for fname, func in testsuites[suite]().testcases.items():
                print(f"* {colorize(fname)}: {colorize(func.__doc__, 96)}")
        print()
        print(f"For help run: {colorize('./main.py -h')}")
        print()
        sys.exit(0)

    try:
        t = suit(sys.argv[1])
    except ValueError as e:
        print(colorize(e))
        print_help()
        sys.exit(1)
    hostport = f"{t.host}:{t.port}"

    batches = list(t.test_batches.keys())
    test_id = None
    if len(sys.argv) > 2:
        if t.TFPATTERN.match(sys.argv[2]):
            test_id = sys.argv[2]
        if re.match("^[\d,]+$", sys.argv[2]):
            batches = sys.argv[2].split(",")

    def print_result(result, print_text_payload=False):
        print("-" * 79)
        print(f"{result['id']}: {colorize(result['description'], 96)}")
        for note in result["notes"]:
            print(f"* {note}")
        if result["errors"]:
            for err in result["errors"]:
                print(colorize(f"[FAILED] {err}"))
        else:
            print(colorize("[PASSED]", 92))
        print()
        print("> " + result["req"]["raw"].replace("\n", "\n> ")[:-2])
        if result["res"]["raw_headers"]:
            print("< " + result["res"]["raw_headers"].replace("\n", "\n< "))
        if result["res"]["payload"]:
            print("< ")
            if print_text_payload and result["res"]["headers"].get("content-type", "text/plain").split('/')[0] in ["text", "message"]:
                print(result["res"]["payload"].decode())
            else:
                print(f"* [Payload redacted ({result['res']['payload_size']} bytes)]")
        print()

    def print_summary(hostport, test_results):
        counts = collections.Counter(test_results.values())
        colors = {"PASSED": 92, "FAILED": 91}
        print("=" * 35, "SUMMARY", "=" * 35)
        print(f"Server: {colorize(hostport, 96)}")
        print("Test Case Results:")
        for test, result in test_results.items():
            print(f"{colorize(result, colors[result])}: {test}")
        print("-" * 79)
        print(f"TOTAL: {len(test_results)}, {colorize('PASSED', 92)}: {counts['PASSED']}, {colorize('FAILED', 91)}: {counts['FAILED']}")
        print("=" * 79)

    print(f"Testing {hostport}")

    try:
        if test_id:
            result = t.run_single_test(test_id)
            print_result(result, print_text_payload=True)
        else:
            test_results = {}
            for batch in batches:
                for result in t.run_batch_tests(batch):
                    test_results[result["id"]] = "FAILED" if result["errors"] else "PASSED"
                    print_result(result)
            print_summary(hostport, test_results)
    except Exception as e:
        print(colorize(e))
