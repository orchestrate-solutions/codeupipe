"""Rust must pass the same conformance cases as Python.

The test needs cargo. On a machine with no cargo it is skipped.
"""

import json
import pathlib
import shutil
import sys

import pytest

CONFORMANCE = pathlib.Path(__file__).resolve().parents[2] / "conformance"
sys.path.insert(0, str(CONFORMANCE))

import run as conformance_run  # noqa: E402



@pytest.mark.skipif(shutil.which("cargo") is None, reason="needs cargo")
def test_rust_passes_every_case():
    cases = conformance_run.load_cases()
    results, error = conformance_run.run_target("rust:run", conformance_run.TARGETS["rust:run"], cases)
    assert error is None, error
    verdicts = {case["id"]: conformance_run.judge(case, results.get(case["id"])) for case in cases}
    not_passed = {case_id: verdict for case_id, verdict in verdicts.items() if verdict[0] != "pass"}
    assert not_passed == {}, json.dumps(not_passed, indent=2)


def test_cargo_is_not_needed_for_the_default_targets(monkeypatch):
    monkeypatch.setattr(conformance_run, "_has_cargo", lambda: False)
    assert [name for name in conformance_run.default_targets() if name.startswith("rust:")] == []
