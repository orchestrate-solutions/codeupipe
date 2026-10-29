"""Go must pass the same conformance cases as Python.

The test needs go. On a machine with no go it is skipped.
"""

import json
import pathlib
import shutil
import sys

import pytest

CONFORMANCE = pathlib.Path(__file__).resolve().parents[2] / "conformance"
sys.path.insert(0, str(CONFORMANCE))

import run as conformance_run  # noqa: E402


@pytest.mark.skipif(shutil.which("go") is None, reason="needs go")
def test_go_passes_every_case():
    cases = conformance_run.load_cases()
    results, error = conformance_run.run_target("go:run", conformance_run.TARGETS["go:run"], cases)
    assert error is None, error
    verdicts = {case["id"]: conformance_run.judge(case, results.get(case["id"])) for case in cases}
    not_passed = {case_id: verdict for case_id, verdict in verdicts.items() if verdict[0] != "pass"}
    assert not_passed == {}, json.dumps(not_passed, indent=2)


def test_go_is_not_needed_for_the_default_targets(monkeypatch):
    monkeypatch.setattr(conformance_run, "_has_go", lambda: False)
    assert [name for name in conformance_run.default_targets() if name.startswith("go:")] == []


def test_the_go_runner_cannot_download():
    env = conformance_run.TARGETS["go:run"]["env"]
    assert env["GOPROXY"] == "off" and env["GOFLAGS"] == "-mod=mod"
