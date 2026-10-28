"""TypeScript must pass the same conformance cases as Python.

The test needs a Node that runs a .ts file as it is (22.18 or later). On a
machine with no such Node it is skipped.
"""

import json
import pathlib
import sys

import pytest

CONFORMANCE = pathlib.Path(__file__).resolve().parents[2] / "conformance"
sys.path.insert(0, str(CONFORMANCE))

import run as conformance_run  # noqa: E402

pytestmark = pytest.mark.skipif(not conformance_run._node_runs_typescript(),
                                reason="needs Node 22.18 or later")


def test_typescript_passes_every_case(tmp_path):
    cases = conformance_run.load_cases()
    results, error = conformance_run.run_target(
        "typescript:run", conformance_run.TARGETS["typescript:run"], cases)
    assert error is None, error
    verdicts = {case["id"]: conformance_run.judge(case, results.get(case["id"])) for case in cases}
    not_passed = {case_id: verdict for case_id, verdict in verdicts.items() if verdict[0] != "pass"}
    assert not_passed == {}, json.dumps(not_passed, indent=2)


@pytest.mark.skipif("typescript:static" not in conformance_run.default_targets(),
                    reason="needs the compile package to be installed")
def test_the_compiled_pipeline_passes_every_case_on_what_it_can_show():
    cases = conformance_run.load_cases()
    results, error = conformance_run.run_target(
        "typescript:static", conformance_run.TARGETS["typescript:static"], cases)
    assert error is None, error
    verdicts = {case["id"]: conformance_run.judge(case, results.get(case["id"])) for case in cases}
    wrong = {case_id: verdict for case_id, verdict in verdicts.items() if verdict[0] not in ("pass", "partial")}
    assert wrong == {}, json.dumps(wrong, indent=2)
    assert sum(1 for verdict in verdicts.values() if verdict[0] == "pass") == 11


def test_a_target_that_cannot_run_is_a_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(conformance_run, "RESULTS", tmp_path)
    monkeypatch.setitem(conformance_run.TARGETS, "broken:run",
                        {"cmd": [sys.executable, "-c", "raise SystemExit(3)"], "env": {}, "cwd": tmp_path})
    assert conformance_run.main(["broken:run"]) == 1


def test_node_is_not_needed_for_the_default_targets(monkeypatch):
    monkeypatch.setattr(conformance_run, "_node_runs_typescript", lambda: False)
    assert [name for name in conformance_run.default_targets() if name.startswith("typescript:")] == []
    assert len([name for name in conformance_run.default_targets() if name.startswith("python:")]) == 5
