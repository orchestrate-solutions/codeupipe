"""Python must pass the cross-runtime conformance suite on every target.

The same cases every runtime is judged by (conformance/README.md), so a
Python change that breaks a shared contract fails here, not later in a
matrix nobody runs.
"""

import json
import pathlib
import subprocess
import sys

import pytest

CONFORMANCE = pathlib.Path(__file__).resolve().parents[2] / "conformance"
PYTHON_TARGETS = ["python:run", "python:run_async", "python:static-steps", "python:static-inline",
                  "python:static-observe"]


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    subprocess.run([sys.executable, str(CONFORMANCE / "run.py"), *PYTHON_TARGETS],
                   capture_output=True, text=True, timeout=600)
    return json.loads((CONFORMANCE / "results" / "latest.json").read_text())


@pytest.mark.parametrize("target", PYTHON_TARGETS)
def test_target_passes_every_case_it_can_express(report, target):
    summary = report["targets"][target]
    assert "error" not in summary, summary.get("error")
    assert summary["FAIL"] == 0, summary["failures"]


def test_observable_export_is_judged_on_state_and_hooks_too(report):
    """No partial passes: static-observe exposes everything the dynamic run does."""
    summary = report["targets"]["python:static-observe"]
    assert summary["pass"] == report["cases"], summary
