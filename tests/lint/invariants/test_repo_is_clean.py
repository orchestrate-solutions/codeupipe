"""This repo's own Python keeps the invariants it lints for."""

import os

from codeupipe_lint.invariants.lint_pipeline import lint_paths

from ._support import REPO

CHECKED = ["packages/codeupipe/codeupipe", "conformance", "scorecard", "packages/codeupipe-lint/codeupipe_lint", "tests", "examples"]


def test_repo_python_has_no_invariant_violations():
    out = lint_paths([os.path.join(REPO, p) for p in CHECKED], exclude=["*/tests/lint/fixtures/*"])
    assert out.get("errors") == []
    # CUP-I008 is a warning, and the framework has logic that cannot be a primitive: it makes the primitives.
    assert [f.format() for f in out.get("findings") if f.rule != "CUP-I008"] == []
    assert out.get("suppressed") == []
