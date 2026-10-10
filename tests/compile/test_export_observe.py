"""Observable static export: ``observe=True``.

The fast export gives up State and Hooks (docs/compile.md). With
``observe=True`` the exported ``run`` records the same State the dynamic
``run`` does and calls Hooks in the same order, so the two modes can be
judged by the same conformance cases, State and Hooks included.
"""

import importlib
import sys

import pytest

from codeupipe import Hook, Payload, Pipeline
from codeupipe.compile import build_export_pipeline_v2


ADD = "_Add"
BOOM = "_Boom"
FAILING_TAP = "_FailingTap"
TAP = "_Tap"
SUB = "SubPipeline"


class SubPipeline(Pipeline):
    """A named pipeline type, so it can be nested (conformance/API.md, step labels)."""


class _Add:
    def call(self, payload):
        return payload.insert("n", payload.get("n", 0) + 1)


class _Boom:
    def call(self, payload):
        raise RuntimeError("boom")


class _FailingTap:
    def observe(self, payload):
        raise RuntimeError("tap boom")


class _Tap:
    def observe(self, payload):
        pass


class _FlagSet:

    def test(self, payload):
        return bool(payload.get('flag'))


class _Record(Hook):
    def __init__(self):
        self.events = []

    def before(self, step, payload):
        self.events.append(("before", step, payload.get("n")))

    def after(self, step, payload):
        self.events.append(("after", step, payload.get("n")))

    def on_error(self, step, error, payload):
        self.events.append(("error", step, str(error)))


def _export(pipeline, tmp_path, observe=True, lowering="steps"):
    out = build_export_pipeline_v2(write=False).run(Payload({
        "pipeline": pipeline, "pattern": "flat", "lowering": lowering, "observe": observe}))
    for f in out.get("files") or []:
        target = tmp_path / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"])
    for name in [m for m in sys.modules if m == "steps" or m.startswith("steps.")]:
        del sys.modules[name]
    sys.path.insert(0, str(tmp_path / "src"))
    try:
        return importlib.import_module("steps")
    finally:
        sys.path.remove(str(tmp_path / "src"))


def _both(pipeline, tmp_path, data, hooked=False):
    """Run dynamic and static on the same input; return (dynamic, static),
    each as (output or error text, state dict, hook events)."""
    dyn_hook, sta_hook = _Record(), _Record()
    if hooked:
        pipeline.use_hook(dyn_hook)
    try:
        dyn_out = pipeline.run(Payload(dict(data))).to_dict()
    except Exception as error:  # noqa: BLE001
        dyn_out = f"error: {error}"
    s = pipeline.state
    dyn_state = {"executed": list(s.executed), "skipped": list(s.skipped),
                 "errors": [name for name, _ in s.errors]}

    package = _export(pipeline, tmp_path)
    state = {}
    try:
        sta_out = package.run(dict(data), state=state, hooks=[sta_hook] if hooked else None)
    except Exception as error:  # noqa: BLE001
        sta_out = f"error: {error}"
    sta_state = {"executed": state["executed"], "skipped": state["skipped"],
                 "errors": [name for name, _ in state["errors"]]}
    return (dyn_out, dyn_state, dyn_hook.events), (sta_out, sta_state, sta_hook.events)


class TestStateMatchesDynamic:
    def test_filters_valves_and_taps(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        p.add_valve(_FlagSet(), _Add())
        p.add_tap(_FailingTap())
        p.add_tap(_Tap())
        dyn, sta = _both(p, tmp_path, {"flag": True})
        assert sta == dyn
        assert sta[1] == {"executed": [ADD, ADD + "#2", FAILING_TAP, TAP], "skipped": [], "errors": [FAILING_TAP]}

    def test_skipped_valve(self, tmp_path):
        p = Pipeline()
        p.add_valve(_FlagSet(), _Add())
        dyn, sta = _both(p, tmp_path, {})
        assert sta == dyn
        assert sta[1]["skipped"] == [ADD]

    def test_failure_keeps_completed_steps(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        p.add_filter(_Boom())
        p.add_filter(_Add())
        dyn, sta = _both(p, tmp_path, {})
        assert sta == dyn
        assert sta[0] == "error: boom" and sta[1]["executed"] == [ADD]

    def test_nested_pipeline_is_one_step(self, tmp_path):
        inner = SubPipeline()
        inner.add_filter(_Add())
        inner.add_valve(_FlagSet(), _Add())
        inner.add_tap(_FailingTap())
        outer = Pipeline()
        outer.add_filter(_Add())
        outer.add_pipeline(inner)
        outer.add_filter(_Add())
        dyn, sta = _both(outer, tmp_path, {})
        assert sta == dyn
        # the inner Valve's skip and Tap error belong to the inner run, as dynamically
        assert sta[1] == {"executed": [ADD, SUB, ADD + "#2"], "skipped": [], "errors": []}


class TestHooksMatchDynamic:
    def test_success_order(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        p.add_tap(_Tap())
        p.add_valve(_FlagSet(), _Add())
        dyn, sta = _both(p, tmp_path, {}, hooked=True)
        assert sta == dyn
        assert [e[:2] for e in sta[2]] == [("before", None), ("before", ADD), ("after", ADD),
                                          ("before", ADD + "#2"), ("after", ADD + "#2"), ("after", None)]

    def test_hooks_see_each_steps_result(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        p.add_filter(_Add())
        dyn, sta = _both(p, tmp_path, {}, hooked=True)
        assert sta[2] == dyn[2]
        assert ("after", ADD + "#2", 2) in sta[2]

    def test_error_order(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        p.add_filter(_Boom())
        dyn, sta = _both(p, tmp_path, {}, hooked=True)
        assert sta == dyn
        assert [e[:2] for e in sta[2]][-2:] == [("error", BOOM), ("error", None)]

    def test_tap_failure_is_not_a_hook_event(self, tmp_path):
        p = Pipeline()
        p.add_tap(_FailingTap())
        dyn, sta = _both(p, tmp_path, {}, hooked=True)
        assert sta == dyn
        assert all(e[0] != "error" for e in sta[2])

    def test_nested_pipeline_gets_one_before_and_after(self, tmp_path):
        inner = SubPipeline()
        inner.add_filter(_Add())
        inner.add_filter(_Add())
        outer = Pipeline()
        outer.add_pipeline(inner)
        dyn, sta = _both(outer, tmp_path, {}, hooked=True)
        assert sta == dyn
        assert [e[:2] for e in sta[2]] == [("before", None), ("before", SUB), ("after", SUB),
                                          ("after", None)]

    def test_failure_inside_nested_pipeline_names_the_nesting_step(self, tmp_path):
        inner = SubPipeline()
        inner.add_filter(_Boom())
        outer = Pipeline()
        outer.add_pipeline(inner)
        dyn, sta = _both(outer, tmp_path, {}, hooked=True)
        assert sta == dyn
        assert [e[:2] for e in sta[2]][-2:] == [("error", SUB), ("error", None)]

    def test_on_error_inside_nested_pipeline_sees_the_payload_it_was_entered_with(self, tmp_path):
        """Scorecard finding F2: the inner run's partial writes never reach
        the outer run dynamically, so the outer on_error must not see them."""
        seen = []

        class _Payloads(Hook):
            def on_error(self, step, error, payload):
                seen.append((step, payload.get("n")))

        inner = SubPipeline()
        inner.add_filter(_Add())
        inner.add_filter(_Boom())
        outer = Pipeline()
        outer.add_filter(_Add())
        outer.add_pipeline(inner)
        outer.use_hook(_Payloads())
        with pytest.raises(RuntimeError):
            outer.run(Payload({}))
        dynamic, seen[:] = list(seen), []
        with pytest.raises(RuntimeError):
            _export(outer, tmp_path).run({}, hooks=[_Payloads()])
        assert seen == dynamic == [(SUB, 1), (None, 1)]


class TestRunArguments:
    def test_hooks_on_the_source_must_be_passed_explicitly(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        p.use_hook(_Record())
        package = _export(p, tmp_path)
        with pytest.raises(TypeError, match="_Record"):
            package.run({})
        assert package.run({}, hooks=()) == {"n": 1}  # an explicit opt-out

    def test_timings_only_when_asked(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        package = _export(p, tmp_path)
        state = {}
        package.run({}, state=state)
        assert state["timings"] == {}
        package.run({}, state=state, timing=True)
        assert set(state["timings"]) == {ADD} and state["timings"][ADD] >= 0

    def test_trace_id_is_recorded(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        state = {}
        _export(p, tmp_path).run({}, state=state, trace_id="t-1")
        assert state["trace_id"] == "t-1"

    def test_a_run_resets_state(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        package = _export(p, tmp_path)
        state = {}
        package.run({}, state=state)
        package.run({}, state=state)
        assert state["executed"] == [ADD]

    def test_state_is_optional(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        assert _export(p, tmp_path).run({"n": 1}) == {"n": 2}

    def test_no_framework_import(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        p.use_hook(_Record())
        out = build_export_pipeline_v2(write=False).run(Payload({"pipeline": p, "observe": True}))
        for f in out.get("files"):
            assert "codeupipe" not in f["content"] and "codeupipe" not in f["content"]


class TestFastExportIsUnchanged:
    def test_hooks_still_refused_without_observe(self, tmp_path):
        from codeupipe.compile.errors import UnsupportedFilterShape

        p = Pipeline()
        p.add_filter(_Add())
        p.use_hook(_Record())
        with pytest.raises(UnsupportedFilterShape):
            _export(p, tmp_path, observe=False)

    def test_nested_pipeline_hooks_refused_even_when_observing(self, tmp_path):
        from codeupipe.compile.errors import UnsupportedFilterShape

        inner = SubPipeline()
        inner.add_filter(_Add())
        inner.use_hook(_Record())
        outer = Pipeline()
        outer.add_pipeline(inner)
        with pytest.raises(UnsupportedFilterShape, match="SubPipeline"):
            _export(outer, tmp_path)

    def test_empty_nested_pipeline_refused_when_observing(self, tmp_path):
        """Scorecard finding F1: it flattens to no steps, so the observable
        export could not report it in State and Hooks as the dynamic run does."""
        from codeupipe.compile.errors import UnsupportedFilterShape

        outer = Pipeline()
        outer.add_filter(_Add())
        outer.add_pipeline(SubPipeline())
        with pytest.raises(UnsupportedFilterShape, match="no steps"):
            _export(outer, tmp_path)
        assert _export(outer, tmp_path / "fast", observe=False).run({}) == {"n": 1}

    def test_inline_layout_cannot_observe(self, tmp_path):
        p = Pipeline()
        p.add_filter(_Add())
        with pytest.raises(ValueError, match="inline"):
            _export(p, tmp_path, lowering="inline")


def test_labels_are_not_code_names(tmp_path):
    """Generated code names steps step_01_... itself; the label (which is
    not an identifier) is only ever a string in State and Hooks."""
    p = Pipeline()
    p.add_filter(_Add())
    p.add_filter(_Add())
    p.add_filter(_Add())
    state = {}
    assert _export(p, tmp_path).run({}, state=state) == {"n": 3}
    assert state["executed"] == [ADD, ADD + "#2", ADD + "#3"]
