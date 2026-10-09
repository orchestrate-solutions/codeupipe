"""The differential harness must pass agreeing modes and catch disagreeing
ones. Planted divergences prove each check can fail."""

import copy

import pytest

from scorecard import differential, modes

CASE = {"id": "t", "hooks": True, "input": {"n": 1, "keep": [1]}, "steps": [
    {"kind": "filter", "name": "s1", "op": "add", "key": "n", "by": 1},
    {"kind": "tap", "name": "t1", "op": "record", "key": "n"},
    {"kind": "tap", "name": "t2", "op": "fail", "message": "sink down"},
    {"kind": "valve", "name": "v1", "when": {"op": "equals", "key": "n", "value": 2},
     "filter": {"op": "append", "key": "keep", "value": 2}},
    {"kind": "pipeline", "name": "p1", "steps": [
        {"kind": "filter", "name": "s2", "op": "mutate", "key": "m", "value": {"x": 1}},
        {"kind": "filter", "name": "s3", "op": "merge", "value": {"z": None}}]},
    {"kind": "filter", "name": "s4", "op": "has", "key": "z", "to": "hz"}]}


def test_an_agreeing_case_passes_every_mode():
    result = differential.check_case(CASE)
    assert result["dynamic"] == []
    for mode, r in result["modes"].items():
        assert r["verdict"] == "pass", (mode, r)


def test_a_failing_filter_is_compared_as_an_error():
    case = copy.deepcopy(CASE)
    case["steps"].append({"kind": "filter", "name": "bad", "op": "fail", "message": "boom"})
    result = differential.check_case(case)
    assert all(r["verdict"] == "pass" for r in result["modes"].values()), result


def _planted(monkeypatch, name, change):
    real = getattr(modes, name)

    def wrapped(*args, **kwargs):
        record = real(*args, **kwargs)
        change(record)
        return record
    monkeypatch.setattr(differential, name, wrapped)


@pytest.mark.parametrize("change,check", [
    (lambda r: r["output"].update(n=99), "outcome"),
    (lambda r: r["output"].update(n=True), "outcome"),   # 2 vs True: == would miss it
    (lambda r: r["taps"].append("extra"), "taps"),
    (lambda r: r.update(input_diff="$['n']: 1 != 2"), "input_mutated"),
    (lambda r: r.update(rerun_diff="$[0]: differs"), "rerun_differs"),
])
def test_planted_fast_divergence_fails(monkeypatch, change, check):
    _planted(monkeypatch, "run_fast", change)
    result = differential.check_case(CASE)
    for mode in ("steps", "inline"):
        assert result["modes"][mode]["verdict"] == "fail"
        assert check in {d["check"] for d in result["modes"][mode]["divergences"]}


@pytest.mark.parametrize("change,check", [
    (lambda r: r["state"]["executed"].pop(), "state.executed"),
    (lambda r: r["state"]["skipped"].append("v1"), "state.skipped"),
    (lambda r: r["state"]["errors"].clear(), "state.errors"),
    (lambda r: r["hooks"].pop(1), "hooks"),
    (lambda r: r.update(isolation=[(3, "after", "s1")]), "payload_mutated_after_the_fact"),
    (lambda r: r.update(source_hooks_guard="did not raise"), "source_hooks_guard"),
])
def test_planted_observe_divergence_fails(monkeypatch, change, check):
    _planted(monkeypatch, "run_observe", change)
    result = differential.check_case(CASE)
    assert result["modes"]["observe"]["verdict"] == "fail"
    assert check in {d["check"] for d in result["modes"]["observe"]["divergences"]}


def test_a_refusal_is_counted_as_refused_not_pass(monkeypatch):
    monkeypatch.setattr(differential, "run_fast",
                        lambda *a, **k: {"status": "refused", "reason": "x.call at line 0:0 — cannot lower Thing."})
    result = differential.check_case(CASE)
    assert result["modes"]["steps"]["verdict"] == "refused"


def test_fast_export_of_a_hooked_pipeline_must_refuse(monkeypatch):
    _planted(monkeypatch, "run_fast", lambda r: r.update(hooks_refused=False))
    result = differential.check_case(CASE)
    assert "hooks_not_refused" in {d["check"] for d in result["modes"]["steps"]["divergences"]}


def test_input_mutation_is_detected_by_the_runner():
    case = {"input": {"a": [1]}}

    def mutating(data):
        data["a"].append(2)
        return data
    record = modes._run_twice(mutating, case)
    assert record["input_diff"]
    assert case["input"] == {"a": [1]}


def test_campaign_report_shape():
    report = differential.run_campaign(seed=5, count=6, hostile_rate=0.0, max_repros=0)
    assert set(report["verdicts"]) == {"steps", "inline", "observe"}
    assert sum(report["verdicts"]["steps"].values()) == 6
    assert "isolation_violations" in report
    assert differential.markdown(report).startswith("# Differential run")
