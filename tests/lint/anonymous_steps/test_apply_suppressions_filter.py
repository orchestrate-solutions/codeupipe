"""ApplySuppressionsFilter: ``cup: allow-anonymous`` comments drop findings."""

import os
import tempfile

from codeupipe import Payload

from codeupipe_lint.anonymous_steps.apply_suppressions_filter import ApplySuppressionsFilter
from codeupipe_lint.anonymous_steps.finding import Finding

SOURCE = """\
p.add_filter(lambda p: p)  # cup: allow-anonymous
p.add_filter(lambda p: p)
# cup: allow-anonymous (intentional: exercises the refusal)
p.add_filter(lambda p: p)
p.add_filter(  // cup: allow-anonymous
    lambda p: p,
)
x = 1  # cup: allow-anonymous
p.add_filter(lambda p: p)
"""


def _finding(path, line, call_line=None):
    return Finding(path, line, 14, "CUP-A001", "lambda-step", "m", "python", call_line)


def test_marker_on_the_line_the_call_line_or_a_comment_line_above():
    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, "x.py")
        with open(path, "w") as handle:
            handle.write(SOURCE)
        findings = [_finding(path, 1), _finding(path, 2), _finding(path, 4), _finding(path, 6, 5),
                    _finding(path, 9)]
        out = ApplySuppressionsFilter().call(Payload({"findings": findings}))
    assert [f.line for f in out.get("findings")] == [2, 9]
    assert [f.line for f in out.get("suppressed")] == [1, 4, 6]


def test_no_findings_is_a_no_op():
    out = ApplySuppressionsFilter().call(Payload({"findings": []}))
    assert out.get("findings") == [] and out.get("suppressed") == []
