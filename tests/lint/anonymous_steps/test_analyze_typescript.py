"""AnalyzeTypescript: anonymous steps in TypeScript, via the compiler API."""

import os
import tempfile

import pytest

from codeupipe_lint.anonymous_steps.analyze_typescript import (BUN_CANDIDATES, DEFAULT_TYPESCRIPT, NODE_CANDIDATES,
                                                     AnalyzeTypescript)
from codeupipe_lint.anonymous_steps.toolchain import find_tool

from ._support import by_line, expectations, fixture, run_analyzer

TYPESCRIPT = os.environ.get("CUP_LINT_TYPESCRIPT") or DEFAULT_TYPESCRIPT
BUN = find_tool("bun", BUN_CANDIDATES)
NODE = find_tool("node", NODE_CANDIDATES)
needs_ts = pytest.mark.skipif(not os.path.isdir(TYPESCRIPT) or not (BUN or NODE),
                              reason="TypeScript compiler (npm ci in runtimes/ts) or bun/node missing")


@needs_ts
@pytest.mark.parametrize("name", ["positive.ts", "negative.ts", "probe.ts"])
def test_fixture_findings_match_expectations(name):
    path = fixture("ts", name)
    findings, errors = run_analyzer(AnalyzeTypescript(), "ts", [path])
    assert errors == []
    assert by_line(findings) == expectations(path)


@needs_ts
@pytest.mark.parametrize("runtime", [r for r in (BUN, NODE) if r])
def test_bun_and_node_agree(runtime):
    path = fixture("ts", "positive.ts")
    findings, errors = run_analyzer(AnalyzeTypescript(runtime=runtime), "ts", [path])
    assert errors == [] and by_line(findings) == expectations(path)


@needs_ts
def test_message_names_the_fix():
    findings, _ = run_analyzer(AnalyzeTypescript(), "ts", [fixture("ts", "probe.ts")])
    first = findings[0]
    assert (first.line, first.col, first.rule) == (14, 13, "CUP-A001")
    assert first.message.startswith("Filter `lambda` is an arrow function. Declare it as a top-level class")


@needs_ts
def test_syntax_error_is_a_finding():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "broken.ts")
        with open(path, "w") as handle:
            handle.write("const = ;\n")
        findings, errors = run_analyzer(AnalyzeTypescript(), "ts", [path])
    assert errors == [] and [f.rule for f in findings] == ["CUP-A000"]


def test_missing_compiler_is_an_error_not_a_pass():
    findings, errors = run_analyzer(AnalyzeTypescript(typescript="/no/such/typescript"), "ts",
                                    [fixture("ts", "probe.ts")])
    assert findings == [] and "TypeScript compiler not found" in errors[0]


def test_missing_runtime_is_an_error_not_a_pass():
    findings, errors = run_analyzer(AnalyzeTypescript(runtime="/no/such/bun"), "ts", [fixture("ts", "probe.ts")])
    assert findings == [] and "no JavaScript runtime" in errors[0]
