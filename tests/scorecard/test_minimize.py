from scorecard import vocab
from scorecard.minimize import minimize


def _has_fail(case):
    return any(s.get("op") == "fail" or s.get("filter", {}).get("op") == "fail"
               for s in vocab.walk_steps(case["steps"]))


def test_shrinks_to_the_one_step_that_matters():
    case = {"id": "c", "hooks": True, "input": {"a": 1, "b": 2}, "steps": [
        {"kind": "filter", "name": "s1", "op": "set", "key": "a", "value": 1},
        {"kind": "pipeline", "name": "p", "steps": [
            {"kind": "tap", "name": "t", "op": "noop"},
            {"kind": "valve", "name": "v", "when": {"op": "truthy", "key": "a"},
             "filter": {"op": "fail", "message": "boom"}}]},
        {"kind": "filter", "name": "s2", "op": "remove", "key": "b"}]}
    small = minimize(case, _has_fail)
    assert small["input"] == {}
    assert small["hooks"] is False
    assert len(small["steps"]) == 1
    assert small["steps"][0]["kind"] == "filter" and small["steps"][0]["op"] == "fail"
    assert small["id"] == "c/min"


def test_keeps_a_name_only_if_the_failure_needs_it():
    case = {"id": "c", "hooks": False, "input": {}, "steps": [
        {"kind": "filter", "name": "data", "op": "set", "key": "a", "value": 1},
        {"kind": "filter", "name": "other", "op": "set", "key": "a", "value": 1}]}
    small = minimize(case, lambda c: any(s["name"] == "data" for s in c["steps"]))
    assert [s["name"] for s in small["steps"]] == ["data"]
    renamed = minimize(case, lambda c: len(c["steps"]) == 2)
    assert all(s["name"] not in ("data", "other") for s in renamed["steps"])
    assert len({s["name"] for s in renamed["steps"]}) == 2  # renames never collide
