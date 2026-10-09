"""This repo's own Python has no anonymous steps, except where a test
exercises the runtime's refusal (suppressed with ``cup: allow-anonymous``)."""

import os

from codeupipe_lint.anonymous_steps.lint_pipeline import lint_paths

from ._support import REPO

CHECKED = ["packages/codeupipe/codeupipe", "conformance/runners/python", "scorecard", "tests/core", "tests/lower",
           "tests/scorecard", "tests/conformance"]
INTENTIONAL = {"tests/core/test_step_identity.py", "tests/lower/test_export_refusals.py"}


def test_repo_python_has_no_anonymous_steps():
    out = lint_paths([os.path.join(REPO, p) for p in CHECKED])
    assert out.get("errors") == []
    assert [f.format() for f in out.get("findings")] == []


def test_suppressions_are_only_in_tests_that_exercise_the_refusal():
    out = lint_paths([os.path.join(REPO, p) for p in CHECKED])
    suppressed = {os.path.relpath(f.path, REPO) for f in out.get("suppressed")}
    assert suppressed and suppressed <= INTENTIONAL
