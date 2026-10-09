"""CUP-I003: a Filter or a Valve predicate must not read pipeline State."""

from codeupipe import Payload
from codeupipe_lint.invariants.analyze_state_reads_filter import AnalyzeStateReadsFilter
from codeupipe_lint.invariants.lint_pipeline import lint_paths
from codeupipe_lint.invariants.parse_python_filter import ParsePythonFilter
from codeupipe_lint.invariants.__main__ import main

from ._support import by_line, expectations, fixture

POSITIVE = fixture("state_read_positive.py")
NEGATIVE = fixture("state_read_negative.py")


def analyze(path):
    parsed = ParsePythonFilter().call(Payload({"files": {"python": [path]}, "findings": [], "errors": []}))
    out = AnalyzeStateReadsFilter().call(parsed)
    return out.get("findings")


def test_flags_exactly_the_marked_lines():
    assert by_line(analyze(POSITIVE)) == expectations(POSITIVE)
    assert len(expectations(POSITIVE)) == 10


def test_flags_only_the_suppressed_line_in_the_negative_fixture():
    source = open(NEGATIVE, encoding="utf-8").read().splitlines()
    flagged = [source[f.line - 1] for f in analyze(NEGATIVE)]
    assert len(flagged) == 1 and "allow-state-read" in flagged[0]


def test_suppression_comment_drops_the_finding():
    out = lint_paths([NEGATIVE])
    assert out.get("findings") == []
    assert len(out.get("suppressed")) == 1


def test_message_shows_the_expression_and_the_fix():
    message = analyze(POSITIVE)[0].message
    assert "self.pipeline.state.executed" in message
    assert "Payload" in message
    assert "Tap" in message


def test_a_syntax_error_is_reported_once_by_the_whole_pipeline(tmp_path):
    bad = tmp_path / "broken.py"
    bad.write_text("class X:\n    def call(self, payload:\n")
    out = lint_paths([str(bad)])
    assert [f.rule for f in out.get("findings")] == ["CUP-I000"]


def test_both_analyzers_run_in_the_pipeline():
    out = lint_paths([POSITIVE, fixture("payload_mutation_positive.py")])
    rules = {f.rule for f in out.get("findings")}
    assert rules == {"CUP-I001", "CUP-I002", "CUP-I003"}


def test_main_lists_the_rule(capsys):
    assert main(["--rules"]) == 0
    assert "CUP-I003  state-read-in-step" in capsys.readouterr().out
