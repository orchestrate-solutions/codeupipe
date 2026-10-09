"""AnalyzePython: anonymous steps in Python source, via ``ast``."""

import os
import tempfile

import pytest

from codeupipe_lint.anonymous_steps.analyze_python import AnalyzePython

from ._support import by_line, expectations, fixture, run_analyzer


@pytest.mark.parametrize("name", ["positive.py", "negative.py", "entry_script.py", "probe.py",
                                  "named_step_api.py", "mixed_api.py"])
def test_fixture_findings_match_expectations(name):
    path = fixture("python", name)
    findings, errors = run_analyzer(AnalyzePython(), "python", [path])
    assert errors == []
    assert by_line(findings) == expectations(path)


def test_negative_fixture_has_no_findings():
    findings, _ = run_analyzer(AnalyzePython(), "python", [fixture("python", "negative.py")])
    assert findings == []


def test_finding_points_at_the_argument_and_names_the_fix():
    path = fixture("python", "probe.py")
    findings, _ = run_analyzer(AnalyzePython(), "python", [path])
    lam = [f for f in findings if f.rule == "CUP-A001"][0]
    assert (lam.line, lam.col) == (31, 14)
    assert lam.slug == "lambda-step"
    assert lam.lang == "python"
    assert "lambda" in lam.message
    assert "module level" in lam.message


def test_valve_predicate_and_inner_are_named_in_the_message():
    path = fixture("python", "positive.py")
    findings, _ = run_analyzer(AnalyzePython(), "python", [path])
    messages = " ".join(f.message for f in findings)
    assert "Valve predicate" in messages
    assert "Valve inner filter" in messages
    assert "Nested pipeline" in messages


def test_syntax_error_is_reported_as_a_finding():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "broken.py")
        with open(path, "w") as handle:
            handle.write("def broken(:\n")
        findings, errors = run_analyzer(AnalyzePython(), "python", [path])
    assert errors == []
    assert [f.rule for f in findings] == ["CUP-A000"]


def test_no_python_files_is_a_no_op():
    findings, errors = run_analyzer(AnalyzePython(), "python", [])
    assert (findings, errors) == ([], [])
