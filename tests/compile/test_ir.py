"""Contract tests for the Pipeline IR dataclasses."""

import ast
import textwrap

import pytest

from codeupipe.compile.ir import (
    HookIR,
    PipelineIR,
    PipelineMeta,
    StepIR,
)


def _fn(src: str) -> ast.FunctionDef:
    return ast.parse(textwrap.dedent(src)).body[0]  # type: ignore[return-value]


class TestPipelineMeta:
    def test_defaults_are_flat_and_cup(self):
        meta = PipelineMeta()
        assert meta.pattern == "flat"
        assert meta.source_hint == "cup"

    def test_is_frozen(self):
        meta = PipelineMeta()
        with pytest.raises((AttributeError, Exception)):
            meta.pattern = "mvc"  # type: ignore[misc]


class TestStepIR:
    def test_minimal_step(self):
        fn = _fn("def call(self, payload):\n    return payload")
        step = StepIR(name="noop", kind="filter", call_ast=fn)
        assert step.name == "noop"
        assert step.kind == "filter"
        assert step.call_ast is fn
        assert step.predicate_ast is None
        assert step.docstring is None
        assert step.source_hint is None

    def test_valve_carries_predicate(self):
        fn = _fn("def call(self, payload):\n    return payload")
        pred = _fn("def _p(data):\n    return True")
        step = StepIR(
            name="gate",
            kind="valve",
            call_ast=fn,
            predicate_ast=pred,
            source_hint="GateFilter",
        )
        assert step.kind == "valve"
        assert step.predicate_ast is pred
        assert step.source_hint == "GateFilter"

    def test_is_frozen(self):
        fn = _fn("def call(self, payload):\n    return payload")
        step = StepIR(name="noop", kind="filter", call_ast=fn)
        with pytest.raises((AttributeError, Exception)):
            step.name = "changed"  # type: ignore[misc]


class TestHookIR:
    def test_all_three_hooks_optional(self):
        hook = HookIR(name="observe")
        assert hook.before_ast is None
        assert hook.after_ast is None
        assert hook.on_error_ast is None


class TestPipelineIR:
    def test_empty_pipeline(self):
        ir = PipelineIR()
        assert ir.steps == []
        assert ir.hooks == []
        assert ir.meta.pattern == "flat"

    def test_step_order_is_preserved(self):
        fn = _fn("def call(self, payload):\n    return payload")
        a = StepIR(name="a", kind="filter", call_ast=fn)
        b = StepIR(name="b", kind="filter", call_ast=fn)
        c = StepIR(name="c", kind="filter", call_ast=fn)
        ir = PipelineIR(steps=[a, b, c])
        assert [s.name for s in ir.steps] == ["a", "b", "c"]
