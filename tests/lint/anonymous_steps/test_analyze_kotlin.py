"""AnalyzeKotlin: anonymous steps in Kotlin source, by lexical scan."""

import pytest

from codeupipe_lint.anonymous_steps.analyze_kotlin import AnalyzeKotlin

from ._support import by_line, expectations, fixture, run_analyzer


@pytest.mark.parametrize("name", ["Positive.kt", "Negative.kt", "Probe.kt", "KnownLimits.kt"])
def test_fixture_findings_match_expectations(name):
    path = fixture("kotlin", name)
    findings, errors = run_analyzer(AnalyzeKotlin(), "kotlin", [path])
    assert errors == []
    assert by_line(findings) == expectations(path)


def test_message_names_the_fix():
    findings, _ = run_analyzer(AnalyzeKotlin(), "kotlin", [fixture("kotlin", "Probe.kt")])
    first = findings[0]
    assert (first.line, first.col, first.rule) == (18, 17, "CUP-A001")
    assert first.message.startswith("Filter is a lambda (Filter { ... }). Declare it at top level")
