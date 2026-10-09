"""CUP-I001 / CUP-I002: a step must not change a Payload behind the API."""

import textwrap

from codeupipe import Payload
from codeupipe_lint.invariants.analyze_payload_mutation_filter import AnalyzePayloadMutationFilter
from codeupipe_lint.invariants.lint_pipeline import lint_paths
from codeupipe_lint.invariants.parse_python_filter import ParsePythonFilter
from codeupipe_lint.invariants.__main__ import main

from ._support import by_line, expectations, fixture

POSITIVE = fixture("payload_mutation_positive.py")
NEGATIVE = fixture("payload_mutation_negative.py")


def analyze(path):
    parsed = ParsePythonFilter().call(Payload({"files": {"python": [path]}, "findings": [], "errors": []}))
    out = AnalyzePayloadMutationFilter().call(parsed)
    return out.get("findings")


def test_flags_exactly_the_marked_lines():
    assert by_line(analyze(POSITIVE)) == expectations(POSITIVE)
    assert len(expectations(POSITIVE)) >= 18


def test_flags_nothing_in_the_negative_fixture_before_suppression():
    lines = by_line(analyze(NEGATIVE))
    source = open(NEGATIVE, encoding="utf-8").read().splitlines()
    unsuppressed = {n: r for n, r in lines.items()
                    if "allow-mutation" not in source[n - 1] and "allow-mutation" not in source[n - 2]}
    assert unsuppressed == {}


def test_suppression_comment_drops_the_finding_and_counts_it():
    out = lint_paths([NEGATIVE])
    assert out.get("findings") == []
    assert len(out.get("suppressed")) == 2
    assert out.get("exit_code") == 0


def test_messages_name_the_variable_and_the_fix():
    messages = {f.rule: f.message for f in analyze(POSITIVE)}
    assert "_data" in messages["CUP-I001"]
    assert "payload.copy()" in messages["CUP-I001"]
    assert "Copy" in messages["CUP-I002"]
    named = [f.message for f in analyze(POSITIVE) if "`items`" in f.message]
    assert named


def test_a_syntax_error_is_reported_not_skipped(tmp_path):
    bad = tmp_path / "broken.py"
    bad.write_text("class X:\n    def call(self, payload:\n")
    out = lint_paths([str(bad)])
    assert [f.rule for f in out.get("findings")] == ["CUP-I000"]
    assert out.get("exit_code") == 1


def test_pipeline_reports_sorted_lines_and_exit_code():
    out = lint_paths([POSITIVE])
    assert out.get("exit_code") == 1
    report = out.get("report").splitlines()
    assert report[0].startswith(POSITIVE + ":6:")
    assert "CUP-I001 payload-internals" in report[0]
    assert report[-1].startswith("%d invariant violations" % len(out.get("findings")))


def test_a_clean_file_reports_none(tmp_path):
    clean = tmp_path / "fine_filter.py"
    clean.write_text(textwrap.dedent("""
        class FineFilter:
            def call(self, payload):
                return payload.insert("a", 1)
    """))
    out = lint_paths([str(clean)])
    assert out.get("exit_code") == 0
    assert out.get("report") == "No invariant violations."


def test_a_missing_path_is_an_error_not_a_clean_run(tmp_path):
    out = lint_paths([str(tmp_path / "nope")])
    assert out.get("exit_code") == 2


def test_main_prints_the_report_and_returns_the_exit_code(capsys):
    assert main([POSITIVE]) == 1
    assert "CUP-I002 shared-value-mutation" in capsys.readouterr().out
    assert main([NEGATIVE]) == 0


def test_main_lists_the_rules(capsys):
    assert main(["--rules"]) == 0
    out = capsys.readouterr().out
    assert "CUP-I001  payload-internals" in out
    assert "CUP-I002  shared-value-mutation" in out
