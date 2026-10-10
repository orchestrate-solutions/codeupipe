"""Static export must refuse, loudly, every shape it cannot reproduce.

Each shape here used to export "successfully" and then behave differently
from the dynamic runtime: Hooks vanished, async steps became broken code,
``payload.trace_id`` became ``data.trace_id`` on a dict, and resilience
wrappers died on an unrelated AttributeError. The contract is in
docs/compile.md: anything that exports behaves the same, and anything
that cannot is refused at export time with the step named.
"""

import asyncio

import pytest

from codeupipe import Hook, Payload, Pipeline
from codeupipe.compile import build_export_pipeline_v2
from codeupipe.compile.errors import UnsupportedFilterShape

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


def _valve(predicate, filter_):
    p = Pipeline()
    p.add_valve(predicate, filter_)
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
        assert "_AsyncAwaits" in _refused(_valve(_Always(), _AsyncAwaits()), lowering)

    def test_valve_with_an_async_predicate(self, lowering):
        assert "predicate" in _refused(_valve(_AsyncPredicate(), _Add()), lowering)

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
def test_a_plain_pipeline_still_exports(lowering):
    assert _export(_one(_Add()), lowering).get("files")



