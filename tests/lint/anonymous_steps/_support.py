"""Shared helpers for the anonymous-step analyzer tests.

Fixtures mark each expected finding with an ``expect: CUP-A00N`` comment on
the line where it is reported (several ids when a line has several).
"""

import os
import re

from codeupipe import Payload

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_EXPECT = re.compile(r"expect:\s*((?:CUP-A\d{3}\s*)+)")


def fixture(lang, name):
    return os.path.join(FIXTURES, lang, name)


def expectations(path):
    """{line: sorted [rule, ...]} from the fixture's ``expect:`` comments."""
    expected = {}
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            match = _EXPECT.search(line)
            if match:
                expected[number] = sorted(match.group(1).split())
    return expected


def by_line(findings):
    """{line: sorted [rule, ...]} from findings."""
    got = {}
    for finding in findings:
        got.setdefault(finding.line, []).append(finding.rule)
    return {line: sorted(rules) for line, rules in got.items()}


def run_analyzer(analyzer, lang, paths):
    """Run one analyzer filter over ``paths``; return (findings, errors)."""
    out = analyzer.call(Payload({"files": {lang: list(paths)}, "findings": [], "errors": []}))
    return out.get("findings"), out.get("errors")
