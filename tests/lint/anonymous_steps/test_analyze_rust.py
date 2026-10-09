"""AnalyzeRust: anonymous steps in Rust source, by lexical scan."""

import pytest

from codeupipe_lint.anonymous_steps.analyze_rust import AnalyzeRust

from ._support import by_line, expectations, fixture, run_analyzer


@pytest.mark.parametrize("name", ["positive.rs", "negative.rs", "probe.rs", "known_limits.rs"])
def test_fixture_findings_match_expectations(name):
    path = fixture("rust", name)
    findings, errors = run_analyzer(AnalyzeRust(), "rust", [path])
    assert errors == []
    assert by_line(findings) == expectations(path)


def test_message_names_the_fix():
    findings, _ = run_analyzer(AnalyzeRust(), "rust", [fixture("rust", "probe.rs")])
    local = [f for f in findings if f.rule == "CUP-A003"][0]
    assert local.message.startswith("Filter is a value of Local, a type declared inside main(). "
                                    "Declare it at module level as a named type")
    assert local.col == 21  # the argument, Box::new(Local)
