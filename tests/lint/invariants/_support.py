"""Fixtures mark each expected finding with an ``expect: CUP-I00N`` comment."""

import os
import re

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "invariants")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_EXPECT = re.compile(r"expect:\s*((?:CUP-I\d{3}\s*)+)")


def fixture(name):
    return os.path.join(FIXTURES, name)


def expectations(path):
    expected = {}
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            match = _EXPECT.search(line)
            if match:
                expected[number] = sorted(match.group(1).split())
    return expected


def by_line(findings):
    got = {}
    for finding in findings:
        got.setdefault(finding.line, []).append(finding.rule)
    return {line: sorted(rules) for line, rules in got.items()}
