"""A State belongs to one run (conformance/API.md, "State").

Two runs of one Pipeline that are in progress at the same time each have
their own State. The conformance cases check a run that starts inside
another run. These tests check runs that really overlap, with asyncio.
"""

import asyncio

from codeupipe import Payload, Pipeline, State


class SlowFilter:
    async def call(self, payload):
        await asyncio.sleep(payload.get("wait"))
        return payload.insert("done", payload.get("name"))


class FailForBFilter:
    def call(self, payload):
        if payload.get("name") == "B":
            raise ValueError("B fails")
        return payload


class IsAPredicate:
    def test(self, payload):
        return payload.get("name") == "A"


class FailTap:
    def observe(self, payload):
        if payload.get("name") == "B":
            raise RuntimeError("the sink is down")


def _overlap(pipeline, give_state):
    """Run A (starts first, ends last) and B (starts second, ends first) at the same time."""
    async def one(name, wait):
        state = State() if give_state else None
        try:
            await pipeline.run_async(Payload({"name": name, "wait": wait}), state)
        except ValueError:
            pass
        return state

    async def both():
        return await asyncio.gather(one("A", 0.05), one("B", 0.01))

    return asyncio.run(both())


def test_each_of_two_runs_at_the_same_time_writes_into_the_state_that_its_caller_gave():
    pipeline = Pipeline()
    pipeline.add_filter(SlowFilter())
    pipeline.add_tap(FailTap())
    pipeline.add_filter(FailForBFilter())
    state_a, state_b = _overlap(pipeline, give_state=True)
    assert state_a.executed == ["SlowFilter", "FailTap", "FailForBFilter"]
    assert state_a.errors == []
    assert state_b.executed == ["SlowFilter", "FailTap"]
    assert [label for label, _error in state_b.errors] == ["FailTap"]


def test_with_no_state_from_the_caller_the_steps_of_two_runs_do_not_mix():
    pipeline = Pipeline()
    pipeline.add_filter(SlowFilter())
    pipeline.add_filter(FailForBFilter())
    _overlap(pipeline, give_state=False)
    # B started last, so the Pipeline has the State of B: the one step that B did, and no step of A.
    assert pipeline.state.executed == ["SlowFilter"]


def test_a_valve_with_an_async_filter_is_skipped_or_run_for_its_own_run():
    pipeline = Pipeline()
    pipeline.add_valve(IsAPredicate(), SlowFilter())
    state_a, state_b = _overlap(pipeline, give_state=True)
    assert (state_a.executed, state_a.skipped) == (["SlowFilter"], [])
    assert (state_b.executed, state_b.skipped) == ([], ["SlowFilter"])


def test_the_pipeline_has_the_state_that_the_caller_gave():
    pipeline = Pipeline()
    pipeline.add_filter(FailForBFilter())
    state = State()
    pipeline.run(Payload({"name": "A"}), state)
    assert pipeline.state is state
    assert state.executed == ["FailForBFilter"]
    pipeline.run(Payload({"name": "A"}))
    assert pipeline.state is not state
    assert state.executed == ["FailForBFilter"]  # a later run does not write into it
