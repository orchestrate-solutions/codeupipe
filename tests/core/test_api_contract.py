"""The CUP API contract, Python side (conformance/API.md).

Cross-runtime semantics live in conformance/cases; these pin the Python
spellings and the rules the shared cases cannot express.
"""

import asyncio

import pytest

from codeupipe import AsyncStepInSyncRun, Hook, Payload, Pipeline


class Inc:
    def call(self, payload):
        return payload.insert("n", payload.get("n", 0) + 1)


class AsyncInc:
    async def call(self, payload):
        return payload.insert("n", payload.get("n", 0) + 1)


INC = f"{__name__}.Inc"
BOOM = f"{__name__}.Boom"


class IncTwice(Pipeline):
    """A named pipeline type: nested pipelines must have one."""

    def __init__(self):
        super().__init__()
        self.add_filter(Inc())


class AsyncHook(Hook):

    async def before(self, step, payload):
        pass


class TestPipelineEntryPoints:
    def test_run_is_synchronous(self):
        p = Pipeline()
        p.add_filter(Inc())
        assert p.run(Payload({"n": 1})).get("n") == 2

    def test_run_async_is_opt_in(self):
        p = Pipeline()
        p.add_filter(AsyncInc())
        assert asyncio.run(p.run_async(Payload({"n": 1}))).get("n") == 2

    def test_run_never_starts_an_event_loop_for_an_async_step(self):
        p = Pipeline()
        p.add_filter(AsyncInc())
        with pytest.raises(AsyncStepInSyncRun, match="AsyncInc"):
            p.run(Payload({}))

    def test_run_never_starts_an_event_loop_for_an_async_hook(self):

        p = Pipeline()
        p.add_filter(Inc())
        p.use_hook(AsyncHook())
        with pytest.raises(AsyncStepInSyncRun):
            p.run(Payload({}))


    def test_nested_pipeline_runs_synchronously_as_one_step(self):
        outer = Pipeline()
        outer.add_filter(Inc())
        outer.add_pipeline(IncTwice())
        assert outer.run(Payload({})).get("n") == 2
        assert outer.state.executed == [INC, f"{__name__}.IncTwice"]


class TestStepsHaveNoNames:
    """Identity is derived from the filter (tests/core/test_step_identity.py)."""

    @pytest.mark.parametrize("add", ["add_filter", "add_tap"])
    def test_a_name_argument_is_rejected(self, add):
        with pytest.raises(TypeError):
            getattr(Pipeline(), add)(Inc(), "a")


class Boom:

    def call(self, payload):
        raise RuntimeError('boom')


class TestHooksReceiveStepIdentities:
    def test_before_after_and_on_error_get_identities(self):
        events = []

        class Record(Hook):
            def before(self, step, payload):
                events.append(("before", step))

            def after(self, step, payload):
                events.append(("after", step))

            def on_error(self, step, error, payload):
                events.append(("error", step))


        p = Pipeline()
        p.add_filter(Inc())
        p.add_filter(Boom())
        p.use_hook(Record())
        with pytest.raises(RuntimeError):
            p.run(Payload({}))
        assert events == [("before", None), ("before", INC), ("after", INC),
                          ("before", BOOM), ("error", BOOM), ("error", None)]


class TestPayloadVocabulary:
    def test_remove_returns_a_new_payload_without_the_key(self):
        p = Payload({"a": 1, "b": 2})
        assert p.remove("a").to_dict() == {"b": 2}
        assert p.to_dict() == {"a": 1, "b": 2}

    def test_remove_of_a_missing_key_is_a_no_op(self):
        assert Payload({"a": 1}).remove("zz").to_dict() == {"a": 1}

    def test_has_is_true_for_a_present_none_value(self):
        p = Payload({"a": None})
        assert p.has("a") and not p.has("b")

    def test_mutable_payload_sets_and_removes_in_place(self):
        m = Payload({"a": 1, "b": 2}).with_mutation()
        m.set("c", 3)
        m.remove("a")
        assert m.to_immutable().to_dict() == {"b": 2, "c": 3}
