"""AnalyzeGo: anonymous steps in Go source, via go/parser + go/ast."""

import os
import tempfile

import pytest

from codeupipe_lint.anonymous_steps.analyze_go import GO_CANDIDATES, AnalyzeGo
from codeupipe_lint.anonymous_steps.toolchain import find_tool

from ._support import by_line, expectations, fixture, run_analyzer

needs_go = pytest.mark.skipif(find_tool("go", GO_CANDIDATES) is None, reason="Go toolchain not installed")


@needs_go
@pytest.mark.parametrize("name", ["positive.go", "negative.go", "probe.go"])
def test_fixture_findings_match_expectations(name):
    path = fixture("go", name)
    findings, errors = run_analyzer(AnalyzeGo(), "go", [path])
    assert errors == []
    assert by_line(findings) == expectations(path)


@needs_go
def test_finding_location_role_and_fix():
    path = fixture("go", "positive.go")
    findings, _ = run_analyzer(AnalyzeGo(), "go", [path])
    pred = [f for f in findings if f.line == 41][0]
    assert (pred.col, pred.rule, pred.slug) == (38, "CUP-A001", "lambda-step")
    assert pred.message.startswith("Valve predicate `pred` is a func literal. Declare it at package level")
    assert pred.path == path


@needs_go
def test_several_files_in_one_run():
    paths = [fixture("go", "positive.go"), fixture("go", "probe.go")]
    findings, _ = run_analyzer(AnalyzeGo(), "go", paths)
    assert {f.path for f in findings} == set(paths)


@needs_go
def test_syntax_error_is_a_finding():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "broken.go")
        with open(path, "w") as handle:
            handle.write("package x\nfunc (\n")
        findings, errors = run_analyzer(AnalyzeGo(), "go", [path])
    assert errors == [] and [f.rule for f in findings] == ["CUP-A000"]


def test_missing_toolchain_is_an_error_not_a_pass():
    findings, errors = run_analyzer(AnalyzeGo(go="/no/such/go"), "go", [fixture("go", "probe.go")])
    assert findings == []
    assert len(errors) == 1 and "Go toolchain not found" in errors[0] and "1 Go file(s) not checked" in errors[0]


def test_no_go_files_does_not_need_the_toolchain():
    findings, errors = run_analyzer(AnalyzeGo(go="/no/such/go"), "go", [])
    assert (findings, errors) == ([], [])
