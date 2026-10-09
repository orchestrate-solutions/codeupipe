"""CUP-I004: only a Filter writes to the Payload."""

from codeupipe import Payload
from codeupipe_lint.invariants.analyze_outside_writes_filter import AnalyzeOutsideWritesFilter
from codeupipe_lint.invariants.lint_pipeline import lint_paths
from codeupipe_lint.invariants.parse_python_filter import ParsePythonFilter
from codeupipe_lint.invariants.__main__ import main

from ._support import by_line, expectations, fixture

POSITIVE = fixture("outside_write_positive.py")
NEGATIVE = fixture("outside_write_negative.py")


def analyze(path):
    parsed = ParsePythonFilter().call(Payload({"files": {"python": [path]}, "findings": [], "errors": []}))
    return AnalyzeOutsideWritesFilter().call(parsed).get("findings")


def test_flags_exactly_the_marked_lines():
    assert by_line(analyze(POSITIVE)) == expectations(POSITIVE)
    assert len(expectations(POSITIVE)) == 11


def test_flags_only_the_suppressed_line_in_the_negative_fixture():
    source = open(NEGATIVE, encoding="utf-8").read().splitlines()
    flagged = [source[f.line - 1] for f in analyze(NEGATIVE)]
    assert len(flagged) == 1 and "allow-outside-write" in flagged[0]


def test_suppression_comment_drops_the_finding():
    out = lint_paths([NEGATIVE])
    assert out.get("findings") == []
    assert len(out.get("suppressed")) == 1


def test_message_names_the_method_and_the_fix():
    message = analyze(POSITIVE)[0].message
    assert "observe" in message
    assert "payload.insert" in message
    assert "Filter" in message


def test_the_rule_runs_in_the_pipeline():
    assert {f.rule for f in lint_paths([POSITIVE]).get("findings")} == {"CUP-I004"}


def test_main_lists_the_rule(capsys):
    assert main(["--rules"]) == 0
    assert "CUP-I004  write-outside-filter" in capsys.readouterr().out
