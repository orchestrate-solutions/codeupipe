"""Static export must refuse, loudly, every shape it cannot reproduce.

Each shape here used to export "successfully" and then behave differently
from the dynamic runtime: Hooks vanished, async steps became broken code,
``payload.trace_id`` became ``data.trace_id`` on a dict, and resilience
wrappers died on an unrelated AttributeError. The contract is in
docs/static-export.md: anything that exports behaves the same, and anything
that cannot is refused at export time with the step named.
"""

import asyncio

import pytest

from codeupipe import Hook, Payload, Pipeline, Valve
from codeupipe.lower import build_export_pipeline_v2
from codeupipe.lower.errors import UnsupportedFilterShape

LOWERINGS = ["steps", "inline"]


class _Add:
    def call(self, payload):
        return payload.insert("n", payload.get("n", 0) + 1)


class _AsyncAwaits:
    async def call(self, payload):
        await asyncio.sleep(0)
        return payload.insert("n", 1)


class _AsyncNoAwait:
    async def call(self, payload):
        return payload.insert("n", 1)


class _Tap:
    def observe(self, payload):
        pass


class _AsyncTap:
    async def observe(self, payload):
        await asyncio.sleep(0)


class _ReadsTrace:
    def call(self, payload):
        return payload.insert("trace", payload.trace_id)


class _ReadsLineage:
    def call(self, payload):
        return payload.insert("hops", len(payload.lineage))


class _SetsTrace:
    def call(self, payload):
        return payload.with_trace("t-1")


class _Hook(Hook):
    pass


class _Always:

    def test(self, payload):
        return True


class _AsyncPredicate:
    async def test(self, payload):
        return True


def _export(pipeline, lowering):
    return build_export_pipeline_v2(write=False).run(
        Payload({"pipeline": pipeline, "pattern": "flat", "lowering": lowering}))


def _refused(pipeline, lowering):
    with pytest.raises(UnsupportedFilterShape) as info:
        _export(pipeline, lowering)
    return str(info.value)


class SubPipeline(Pipeline):
    """A named pipeline type, so it can be nested."""


def _one(step, kind=Pipeline):
    p = kind()
    p.add_filter(step)
    return p


@pytest.mark.parametrize("lowering", LOWERINGS)
class TestHooksAreRefused:
    def test_hook_on_the_exported_pipeline(self, lowering):
        p = _one(_Add())
        p.use_hook(_Hook())
        assert "Hook" in _refused(p, lowering)

    def test_hook_on_a_nested_pipeline(self, lowering):
        inner = _one(_Add(), SubPipeline)
        inner.use_hook(_Hook())
        outer = Pipeline()
        outer.add_pipeline(inner)
        assert "SubPipeline" in _refused(outer, lowering)


@pytest.mark.parametrize("lowering", LOWERINGS)
class TestAsyncStepsAreRefused:
    """Static ``run`` is sync, like the dynamic ``run``, which raises
    AsyncStepInSyncRun on the same pipelines."""

    def test_async_filter_that_awaits(self, lowering):
        assert "_AsyncAwaits" in _refused(_one(_AsyncAwaits()), lowering)

    def test_async_filter_without_await(self, lowering):
        assert "_AsyncNoAwait" in _refused(_one(_AsyncNoAwait()), lowering)

    def test_async_tap(self, lowering):
        p = _one(_Add())
        p.add_tap(_AsyncTap())
        assert "_AsyncTap" in _refused(p, lowering)

    def test_valve_around_an_async_filter(self, lowering):
        assert "_AsyncAwaits" in _refused(_one(Valve(_AsyncAwaits(), _Always())), lowering)

    def test_valve_with_an_async_predicate(self, lowering):
        assert "predicate" in _refused(_one(Valve(_Add(), _AsyncPredicate())), lowering)

    def test_dynamic_run_refuses_the_same_pipeline(self, lowering):
        from codeupipe.core import AsyncStepInSyncRun

        with pytest.raises(AsyncStepInSyncRun):
            _one(_AsyncAwaits()).run(Payload({}))


@pytest.mark.parametrize("lowering", LOWERINGS)
class TestTraceAndLineageAreRefused:
    def test_reading_trace_id(self, lowering):
        message = _refused(_one(_ReadsTrace()), lowering)
        assert "_ReadsTrace" in message and "trace_id" in message

    def test_reading_lineage(self, lowering):
        assert "lineage" in _refused(_one(_ReadsLineage()), lowering)

    def test_setting_trace(self, lowering):
        assert "with_trace" in _refused(_one(_SetsTrace()), lowering)


@pytest.mark.parametrize("lowering", LOWERINGS)
class TestResilienceWrappersAreRefused:
    @pytest.mark.parametrize("wrap", [
        lambda p: p.with_retry(3),
        lambda p: p.with_timeout(1.0),
        lambda p: p.with_circuit_breaker(2),
        lambda p: p.with_rate_limit(10.0),
    ], ids=["retry", "timeout", "circuit_breaker", "rate_limit"])
    def test_wrapped_pipeline(self, lowering, wrap):
        message = _refused(wrap(_one(_Add())), lowering)
        assert "wrapper" in message and "export the inner Pipeline" in message

    def test_wrapped_pipeline_nested_inside_another(self, lowering):
        outer = Pipeline()
        outer.add_pipeline(_one(_Add()).with_retry(3))
        assert "_RetryPipeline" in _refused(outer, lowering)


@pytest.mark.parametrize("lowering", LOWERINGS)
def test_a_plain_pipeline_still_exports(lowering):
    assert _export(_one(_Add()), lowering).get("files")


def _callback(event):
    pass


@pytest.mark.parametrize("lowering", LOWERINGS)
class TestRunTimeBehaviourOnThePipelineIsRefused:
    """Settings on the Pipeline itself that change what run() does. The
    exported run() ignored every one of them."""

    def test_required_input_keys(self, lowering):
        p = _one(_Add())
        p.require_input("x")
        assert "require_input" in _refused(p, lowering)

    def test_guaranteed_output_keys(self, lowering):
        p = _one(_Add())
        p.guarantee_output("n")
        assert "guarantee_output" in _refused(p, lowering)

    def test_event_listeners(self, lowering):
        p = _one(_Add())
        p.on("*", _callback)
        assert "event listeners" in _refused(p, lowering)

    def test_disabled_taps(self, lowering):
        p = _one(_Add())
        p.add_tap(_Tap())
        p._disabled_taps = frozenset({f"{__name__}._Tap"})
        assert f"{__name__}._Tap" in _refused(p, lowering)

    def test_contract_on_a_nested_pipeline(self, lowering):
        inner = _one(_Add(), SubPipeline)
        inner.require_input("x")
        outer = Pipeline()
        outer.add_pipeline(inner)
        assert "SubPipeline" in _refused(outer, lowering)
