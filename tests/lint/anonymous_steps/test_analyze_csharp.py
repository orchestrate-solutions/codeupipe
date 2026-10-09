"""AnalyzeCsharp: anonymous steps in C# source, by lexical scan."""

import pytest

from codeupipe_lint.anonymous_steps.analyze_csharp import AnalyzeCsharp

from ._support import by_line, expectations, fixture, run_analyzer


@pytest.mark.parametrize("name", ["Positive.cs", "Negative.cs", "Probe.cs", "KnownLimits.cs"])
def test_fixture_findings_match_expectations(name):
    path = fixture("csharp", name)
    findings, errors = run_analyzer(AnalyzeCsharp(), "csharp", [path])
    assert errors == []
    assert by_line(findings) == expectations(path)


def test_message_names_the_fix():
    findings, _ = run_analyzer(AnalyzeCsharp(), "csharp", [fixture("csharp", "Probe.cs")])
    first = findings[0]
    assert (first.line, first.rule) == (27, "CUP-A001")
    assert first.message.startswith("Valve predicate is a lambda. Declare it as a named class")


def test_top_level_statement_functions_are_local():
    import os
    import tempfile
    source = "using CupPipe;\nbool IsOn(Payload p) => true;\nvar p = new Pipeline();\n" \
             "p.AddFilter(new Valve(\"v\", new Named(), IsOn), \"v\");\n"
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "Program.cs")
        with open(path, "w") as handle:
            handle.write(source)
        findings, _ = run_analyzer(AnalyzeCsharp(), "csharp", [path])
    assert [(f.line, f.rule) for f in findings] == [(4, "CUP-A002")]
