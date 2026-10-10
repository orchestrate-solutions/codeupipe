"""add_valve(predicate, filter): the one way to add a Valve to a Pipeline.

The condition comes first, then the Filter that it controls.
"""

import asyncio

import pytest

import codeupipe
from codeupipe import Payload, Pipeline
from codeupipe.core.valve import Valve

HERE = __name__


class SetA:
    def call(self, payload):
        return payload.insert("a", 1)


class AsyncSetA:
    async def call(self, payload):
        return payload.insert("a", 1)


class IsOn:
    def test(self, payload):
        return payload.get("on") is True


class AtLeast:
    def __init__(self, key, minimum):
        self.key = key
        self.minimum = minimum

    def test(self, payload):
        return payload.get(self.key, 0) >= self.minimum


def test_the_filter_runs_when_the_predicate_is_true():
    pipeline = Pipeline()
    pipeline.add_valve(IsOn(), SetA())
    assert pipeline.run(Payload({"on": True})).to_dict() == {"on": True, "a": 1}
    assert pipeline.state.executed == ["SetA"]
    assert pipeline.state.skipped == []


def test_the_payload_passes_through_when_the_predicate_is_false():
    pipeline = Pipeline()
    pipeline.add_valve(IsOn(), SetA())
    assert pipeline.run(Payload({"on": False})).to_dict() == {"on": False}
    assert pipeline.state.executed == []
    assert pipeline.state.skipped == ["SetA"]


def test_a_valve_is_identified_by_its_filter():
    pipeline = Pipeline()
    pipeline.add_valve(IsOn(), SetA())
    pipeline.add_valve(AtLeast("n", 2), SetA())
    assert pipeline.labels == ["SetA", "SetA#2"]


def test_a_predicate_keeps_its_settings():
    pipeline = Pipeline()
    pipeline.add_valve(AtLeast("qty", 10), SetA())
    assert pipeline.run(Payload({"qty": 10})).get("a") == 1
    assert pipeline.run(Payload({"qty": 9})).has("a") is False


def test_named_arguments():
    pipeline = Pipeline()
    pipeline.add_valve(predicate=IsOn(), filter=SetA())
    assert pipeline.run(Payload({"on": True})).get("a") == 1


def test_an_async_filter_behind_a_valve_needs_run_async():
    pipeline = Pipeline()
    pipeline.add_valve(IsOn(), AsyncSetA())
    with pytest.raises(codeupipe.AsyncStepInSyncRun):
        pipeline.run(Payload({"on": True}))
    assert asyncio.run(pipeline.run_async(Payload({"on": True}))).get("a") == 1


def test_a_function_is_not_a_predicate():
    def is_on(payload):
        return True
    with pytest.raises(TypeError, match=r"test\(payload\)"):
        Pipeline().add_valve(is_on, SetA())  # cup: allow-anonymous (exercises the refusal)


def test_the_arguments_in_the_wrong_order_are_refused_with_the_fix():
    with pytest.raises(TypeError, match=r"add_valve\(predicate, filter\)"):
        Pipeline().add_valve(SetA(), IsOn())


def test_add_filter_refuses_a_valve_and_names_add_valve():
    with pytest.raises(TypeError, match="add_valve"):
        Pipeline().add_filter(Valve(SetA(), IsOn()))


def test_valve_is_not_a_public_name():
    assert "Valve" not in codeupipe.__all__
    assert not hasattr(codeupipe, "Valve")
