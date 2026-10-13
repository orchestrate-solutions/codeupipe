"""This repo's own Python keeps the invariants it lints for."""

import os

from codeupipe_lint.invariants.lint_pipeline import lint_paths

from ._support import REPO

# The places with a `cup: allow-plain` comment.
PLAIN_BY_DESIGN = 81

CHECKED = ["packages/codeupipe/codeupipe", "conformance", "scorecard", "packages/codeupipe-lint/codeupipe_lint", "tests", "examples"]


def test_repo_python_has_no_invariant_violations():
    out = lint_paths([os.path.join(REPO, p) for p in CHECKED], exclude=["*/tests/lint/fixtures/*"])
    assert out.get("errors") == []
    # No finding and no warning: the repository passes its own linter in strict mode.
    assert [f.format() for f in out.get("findings")] == []
    # The only comments that allow a finding are for CUP-I008, on code that is plain for a reason that
    # the comment gives: a primitive itself, a visitor of a syntax tree, the entry of a program, a test
    # harness. The number is here so that a new one is a change that someone sees.
    allowed = out.get("suppressed")
    assert {f.rule for f in allowed} == {"CUP-I008"}
    assert len(allowed) == PLAIN_BY_DESIGN, sorted({f.path for f in allowed})
