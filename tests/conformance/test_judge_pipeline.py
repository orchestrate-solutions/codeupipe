"""The judge is a pipeline, so each of its steps is tested alone, with no runner and no process."""

import json
import pathlib
import sys

import pytest

CONFORMANCE = pathlib.Path(__file__).resolve().parents[2] / "conformance"
sys.path.insert(0, str(CONFORMANCE))

from codeupipe import Payload  # noqa: E402

from judging.default_targets_filter import DefaultTargetsFilter  # noqa: E402
from judging.judge_pipeline import JudgePipeline  # noqa: E402
from judging.judge_results_filter import JudgeResultsFilter  # noqa: E402
from judging.load_cases_filter import LoadCasesFilter  # noqa: E402

CASE = {"id": "a/one", "steps": [], "input": {"n": 1},
        "expect": {"output": {"n": 2}, "state": {"executed": ["s"], "skipped": [], "errors": []}, "hooks": ["before:"]}}
GOOD = {"id": "a/one", "output": {"n": 2.0}, "state": {"executed": ["s"], "skipped": [], "errors": []},
        "hooks": ["before:"], "taps": [], "input_after": {"n": 1}}


def without(result, *keys):
    return {key: value for key, value in result.items() if key not in keys}


@pytest.mark.parametrize("result, status, problem", [
    (GOOD, "pass", None),
    (None, "FAIL", "no result from runner"),
    ({"id": "a/one", "unsupported": "no nested pipeline"}, "unsupported", "no nested pipeline"),
    (without(GOOD, "state", "hooks"), "partial", "target cannot observe state, hooks"),
    ({**GOOD, "output": {"n": 3}}, "FAIL", "output {'n': 3} != {'n': 2}"),
    ({**GOOD, "output": {"n": True}}, "FAIL", "output {'n': True} != {'n': 2}"),
    ({**without(GOOD, "output"), "error": "ValueError: no"}, "FAIL", "expected output, got error 'ValueError: no'"),
    ({**GOOD, "input_after": {"n": 9}}, "FAIL", "input was mutated: {'n': 9}"),
    ({**GOOD, "state": {"executed": [], "skipped": [], "errors": []}}, "FAIL", "state.executed [] != ['s']"),
    ({**GOOD, "hooks": []}, "FAIL", "hooks [] != ['before:']"),
])
def test_the_verdict_for_one_result(result, status, problem):
    got_status, problems = JudgeResultsFilter().judge(CASE, result)
    assert got_status == status
    assert problems == ([] if problem is None else [problem])


def test_an_error_is_expected_by_a_part_of_its_message():
    case = {"id": "a/two", "steps": [], "input": {}, "expect": {"error": {"message_contains": "boom"}}}
    judge = JudgeResultsFilter().judge
    assert judge(case, {"error": "ValueError: boom!", "input_after": {}})[0] == "pass"
    assert judge(case, {"error": "ValueError: other", "input_after": {}})[0] == "FAIL"
    assert judge(case, {"output": {}, "input_after": {}})[0] == "FAIL"


def test_a_python_target_always_runs_and_a_typescript_target_needs_node_and_its_files(tmp_path):
    there = tmp_path / "built.js"
    there.write_text("")
    targets = {"python:run": {}, "typescript:run": {}, "typescript:static": {}, "typescript:other": {}}
    needs = {"typescript:static": [there], "typescript:other": [tmp_path / "missing.js"]}
    assert DefaultTargetsFilter(lambda: True).choose(targets, needs) == ["python:run", "typescript:run", "typescript:static"]
    assert DefaultTargetsFilter(lambda: False).choose(targets, needs) == ["python:run"]


def test_a_rust_target_needs_cargo():
    targets = {"python:run": {}, "rust:run": {}}
    assert DefaultTargetsFilter(lambda: False, lambda: True).choose(targets, {}) == ["python:run", "rust:run"]
    assert DefaultTargetsFilter(lambda: False, lambda: False).choose(targets, {}) == ["python:run"]


def test_a_go_target_needs_go():
    targets = {"python:run": {}, "rust:run": {}, "go:run": {}}
    assert DefaultTargetsFilter(lambda: False, lambda: False, has_go=lambda: True).choose(targets, {}) == [
        "python:run", "go:run"]
    assert DefaultTargetsFilter(lambda: False, lambda: True, has_go=lambda: False).choose(targets, {}) == [
        "python:run", "rust:run"]


def test_two_cases_with_one_id_stop_the_run(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps([{"id": "x"}, {"id": "x"}]))
    with pytest.raises(SystemExit, match="duplicate case ids"):
        LoadCasesFilter().load(tmp_path)


class FakeLauncher:
    """A launcher that starts no process: it gives the results that the test made."""

    def __init__(self, by_command):
        self.by_command = by_command

    def run(self, spec, cases):
        return self.by_command[spec["cmd"]]


def test_the_whole_judge_with_no_process(tmp_path):
    cases_dir, results_dir = tmp_path / "cases", tmp_path / "results"
    cases_dir.mkdir()
    (cases_dir / "a.json").write_text(json.dumps([CASE]))
    launcher = FakeLauncher({
        "good": ({"a/one": GOOD}, None),
        "wrong": ({"a/one": {**GOOD, "output": {"n": 3}}}, None),
        "broken": (None, "runner exited 3: no"),
    })
    targets = {"t:good": {"cmd": "good"}, "t:wrong": {"cmd": "wrong"}, "t:broken": {"cmd": "broken"}}
    pipeline = JudgePipeline(launcher, lambda: False)

    def run(names):
        return pipeline.run(Payload({"cases_dir": cases_dir, "results_dir": results_dir, "targets": targets,
                                     "needs": {}, "names": names}))

    out = run(["t:good"])
    assert out.get("exit_code") == 0
    assert out.get("matrix") == {"a/one": {"t:good": "pass"}}
    assert json.loads((results_dir / "latest.json").read_text()) == out.get("report")
    assert (results_dir / "latest.md").read_text() == out.get("markdown")

    out = run(["t:good", "t:wrong", "t:broken"])
    assert out.get("exit_code") == 1
    assert out.get("matrix") == {"a/one": {"t:good": "pass", "t:wrong": "FAIL", "t:broken": "—"}}
    assert out.get("report")["targets"]["t:wrong"]["failures"] == {"a/one": ["output {'n': 3} != {'n': 2}"]}
    assert out.get("report")["targets"]["t:broken"] == {"error": "runner exited 3: no"}
    assert "- **t:broken**: not run: runner exited 3: no" in out.get("markdown")

    # With no target named, the judge takes each target that the machine can run.
    assert set(run([]).get("matrix")["a/one"]) == {"t:good", "t:wrong", "t:broken"}
    assert pipeline.state.executed[1] == "DefaultTargetsFilter"
    run(["t:good"])
    assert pipeline.state.skipped == ["DefaultTargetsFilter"]
