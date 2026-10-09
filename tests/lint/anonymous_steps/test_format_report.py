"""FormatReport: sorted ``path:line:col  RULE slug  message`` lines and an exit code."""

from codeupipe import Payload

from codeupipe_lint.anonymous_steps.finding import Finding
from codeupipe_lint.anonymous_steps.format_report import FormatReport


def _f(path, line, col, rule="CUP-A001", slug="lambda-step"):
    return Finding(path, line, col, rule, slug, "Filter is a lambda. Fix it.", "python")


def test_findings_are_sorted_and_formatted_with_a_summary():
    findings = [_f("b.py", 1, 1), _f("a.py", 9, 3), _f("a.py", 2, 5, "CUP-A003", "local-type-step")]
    out = FormatReport().call(Payload({"findings": findings, "errors": [], "suppressed": [_f("c.py", 1, 1)]}))
    assert out.get("report").splitlines() == [
        "a.py:2:5  CUP-A003 local-type-step  Filter is a lambda. Fix it.",
        "a.py:9:3  CUP-A001 lambda-step  Filter is a lambda. Fix it.",
        "b.py:1:1  CUP-A001 lambda-step  Filter is a lambda. Fix it.",
        "3 anonymous steps (1 suppressed).",
    ]
    assert out.get("exit_code") == 1


def test_clean_run_exits_zero():
    out = FormatReport().call(Payload({"findings": [], "errors": [], "suppressed": []}))
    assert out.get("report") == "No anonymous steps."
    assert out.get("exit_code") == 0


def test_an_analyzer_that_could_not_run_exits_two():
    out = FormatReport().call(Payload({"findings": [_f("a.py", 1, 1)], "errors": ["go: not found"],
                                       "suppressed": []}))
    assert out.get("exit_code") == 2
    assert "go: not found" in out.get("error_report")
