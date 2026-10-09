"""AnalyzeCpp: anonymous steps in C++ source, by lexical scan."""

import pytest

from codeupipe_lint.anonymous_steps.analyze_cpp import AnalyzeCpp

from ._support import by_line, expectations, fixture, run_analyzer


@pytest.mark.parametrize("name", ["positive.cpp", "negative.cpp", "probe.cpp", "known_limits.cpp"])
def test_fixture_findings_match_expectations(name):
    path = fixture("cpp", name)
    findings, errors = run_analyzer(AnalyzeCpp(), "cpp", [path])
    assert errors == []
    assert by_line(findings) == expectations(path)


def test_message_names_the_fix():
    findings, _ = run_analyzer(AnalyzeCpp(), "cpp", [fixture("cpp", "probe.cpp")])
    by_rule = {f.rule: f for f in findings}
    assert by_rule["CUP-A003"].message.startswith(
        "Filter is a Local, a type defined inside main(). Declare it at namespace scope as a named struct")
    assert by_rule["CUP-A007"].message.startswith(
        "Filter is the free function app::filters::normalize. A free function has no derivable name")
    assert (by_rule["CUP-A007"].line, by_rule["CUP-A007"].col) == (17, 18)
