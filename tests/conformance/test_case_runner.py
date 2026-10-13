"""The Python runner is two pipelines, so each of its steps is tested alone."""

import pathlib
import sys

import pytest

RUNNER = pathlib.Path(__file__).resolve().parents[2] / "conformance" / "runners" / "python"
sys.path.insert(0, str(RUNNER))

from codeupipe import Payload, Pipeline  # noqa: E402

import conformance_sink as sink  # noqa: E402
from case_runner.attach_record_hook_filter import AttachRecordHookFilter  # noqa: E402
from case_runner.build_pipeline_filter import BuildPipelineFilter  # noqa: E402
from case_runner.name_steps_filter import NameStepsFilter  # noqa: E402
from case_runner.parse_target_filter import ParseTargetFilter  # noqa: E402
from case_runner.run_case_pipeline import RunCasePipeline  # noqa: E402
from case_runner.run_each_case_filter import RunEachCaseFilter  # noqa: E402
from case_runner.unsupported import Unsupported  # noqa: E402
from case_runner.write_predicates_filter import WritePredicatesFilter  # noqa: E402

VALVE = {"kind": "valve", "name": "gate", "when": {"op": "truthy", "key": "on"}, "filter": {"op": "set", "key": "b", "value": 2}}
CASE = {"id": "t/one", "steps": [{"kind": "filter", "name": "first", "op": "set", "key": "a", "value": 1}, VALVE,
                                 {"kind": "tap", "name": "audit", "op": "record", "key": "a"}], "input": {"on": True}}


@pytest.mark.parametrize("target, compiled, run_async, lowering, observe", [
    ("run", False, False, "", False), ("run_async", False, True, "", False),
    ("static-steps", True, False, "steps", False), ("static-inline", True, False, "inline", False),
    ("static-observe", True, False, "steps", True),
])
def test_what_the_name_of_a_target_means(target, compiled, run_async, lowering, observe):
    out = ParseTargetFilter().call(Payload({"target": target}))
    assert (out.get("compiled"), out.get("run_async"), out.get("lowering"), out.get("observe")) == (compiled, run_async, lowering, observe)


def test_a_name_that_is_not_a_target_stops_the_runner():
    with pytest.raises(SystemExit, match="unknown target 'nope'"):
        ParseTargetFilter().call(Payload({"target": "nope"}))
    with pytest.raises(SystemExit, match="unknown bench target 'run_async'"):
        ParseTargetFilter(("run",), "bench target").call(Payload({"target": "run_async"}))


def built(tmp_path, case=CASE, run_async=False):
    payload = Payload({"case": case, "workdir": tmp_path, "module_name": f"t_predicates_{abs(hash(tmp_path))}", "run_async": run_async})
    return BuildPipelineFilter().call(WritePredicatesFilter().call(payload))


def test_a_predicate_of_a_case_is_a_real_class_with_test(tmp_path):
    predicates = WritePredicatesFilter().call(Payload({"case": CASE, "workdir": tmp_path, "module_name": "t_predicates_a"})).get("predicates")
    assert predicates.when_gate.test(Payload({"on": 1})) is True
    assert predicates.when_gate.test(Payload({})) is False
    assert type(predicates.when_gate).__name__ == "When_gate"


def test_the_pipeline_of_a_case_and_the_name_of_each_label(tmp_path):
    out = built(tmp_path)
    assert isinstance(out.get("pipeline"), Pipeline)
    assert out.get("label") == {"SetFilter": "first", "SetFilter#2": "gate", "RecordTap": "audit"}


@pytest.mark.parametrize("step, message", [
    ({"kind": "filter", "name": "a", "op": "nope"}, "unknown filter op 'nope'"),
    ({"kind": "tap", "name": "a", "op": "nope"}, "unknown tap op 'nope'"),
    ({"kind": "nope", "name": "a"}, "unknown step kind 'nope'"),
])
def test_a_word_that_the_runner_does_not_know_is_unsupported(tmp_path, step, message):
    with pytest.raises(Unsupported, match=message):
        built(tmp_path, {"id": "t/x", "steps": [step], "input": {}})


def test_a_hook_is_attached_for_a_case_that_asks_and_a_target_that_calls_hooks(tmp_path):
    def hooks(case_hooks, compiled, observe):
        payload = built(tmp_path, {**CASE, "hooks": case_hooks}).insert("compiled", compiled).insert("observe", observe)
        return AttachRecordHookFilter().call(payload).get("hooks")

    assert hooks(False, False, False) is None
    assert len(hooks(True, False, False)) == 1   # the dynamic run
    assert hooks(True, True, False) is None      # fast compiled code calls no Hooks
    assert len(hooks(True, True, True)) == 1     # compiled with observe


def test_each_step_in_a_result_gets_the_name_of_the_case():
    result = {"output": {}, "state": {"executed": ["SetFilter", "Other"], "skipped": ["SetFilter#2"], "errors": []},
              "inner_states": [{"executed": ["SetFilter#2"], "skipped": [], "errors": ["SetFilter"]}],
              "hooks": ["before:", "before:SetFilter", "error:SetFilter#2"]}
    named = NameStepsFilter().call(Payload({"result": result, "label": {"SetFilter": "first", "SetFilter#2": "gate"}})).get("result")
    assert named["state"] == {"executed": ["first", "Other"], "skipped": ["gate"], "errors": []}
    assert named["inner_states"] == [{"executed": ["gate"], "skipped": [], "errors": ["first"]}]
    assert named["hooks"] == ["before:", "before:first", "error:gate"]


@pytest.mark.parametrize("target", ["run", "run_async", "static-steps", "static-inline", "static-observe"])
def test_one_case_on_each_target(tmp_path, target):
    sink.reset()
    out = RunCasePipeline().run(Payload({"case": CASE, "target": target, "workdir": tmp_path, "module_name": f"t_case_{target.replace('-', '_')}"}))
    result = out.get("result")
    assert result["output"] == {"on": True, "a": 1, "b": 2}
    assert result["taps"] == [1]
    assert result["input_after"] == {"on": True}
    assert ("state" in result) == (target not in ("static-steps", "static-inline"))
    assert result.get("state", {"executed": ["first", "gate", "audit"]})["executed"] == ["first", "gate", "audit"]


def test_a_case_that_a_target_cannot_express_is_reported_and_the_next_case_still_runs():
    cases = [{"id": "t/bad", "steps": [{"kind": "filter", "name": "a", "op": "nope"}], "input": {}}, CASE]
    results = RunEachCaseFilter(RunCasePipeline()).call(Payload({"cases": cases, "target": "run"})).get("results")
    assert results[0] == {"id": "t/bad", "unsupported": "unknown filter op 'nope'"}
    assert results[1]["id"] == "t/one" and results[1]["output"] == {"on": True, "a": 1, "b": 2}
