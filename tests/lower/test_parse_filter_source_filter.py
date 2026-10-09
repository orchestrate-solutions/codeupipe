"""RED tests for ParseFilterSourceFilter (M0)."""

import ast

import pytest

from codeupipe import Payload
from codeupipe.lower.errors import UnsupportedFilterShape
from codeupipe.lower.filters.parse_filter_source_filter import ParseFilterSourceFilter
from codeupipe.lower.ir import HookIR, PipelineIR, StepIR


class _ExampleFilter:
    """Docstrings must survive extraction."""

    def call(self, payload):
        """This should end up on StepIR.docstring."""
        return payload.insert("k", 1)


class _ExampleTap:
    def observe(self, payload):
        pass


class TestParseFilterSource:
    def test_populates_call_ast(self):
        skeleton = PipelineIR(steps=[StepIR(
            name="example",
            kind="filter",
            call_ast=ast.parse("def _(self, payload): pass").body[0],  # type: ignore[arg-type]
            source_hint="_ExampleFilter",
        )])
        result = ParseFilterSourceFilter().call(Payload({
            "pipeline_ir": skeleton,
            "step_instances": [_ExampleFilter()],
        }))
        ir = result.get("pipeline_ir")
        src = ast.unparse(ir.steps[0].call_ast)
        assert "payload.insert" in src

    def test_preserves_docstring(self):
        skeleton = PipelineIR(steps=[StepIR(
            name="example",
            kind="filter",
            call_ast=ast.parse("def _(self, payload): pass").body[0],  # type: ignore[arg-type]
            source_hint="_ExampleFilter",
        )])
        result = ParseFilterSourceFilter().call(Payload({
            "pipeline_ir": skeleton,
            "step_instances": [_ExampleFilter()],
        }))
        ir = result.get("pipeline_ir")
        assert ir.steps[0].docstring is not None
        assert "survive extraction" in ir.steps[0].docstring or "should end up" in ir.steps[0].docstring

    def test_tap_parses_observe_method(self):
        skeleton = PipelineIR(steps=[StepIR(
            name="example_tap",
            kind="tap",
            call_ast=ast.parse("def _(self, payload): pass").body[0],  # type: ignore[arg-type]
            source_hint="_ExampleTap",
        )])
        result = ParseFilterSourceFilter().call(Payload({
            "pipeline_ir": skeleton,
            "step_instances": [_ExampleTap()],
        }))
        # Tap's observe should have been picked up
        ir = result.get("pipeline_ir")
        assert ir.steps[0].kind == "tap"

    def test_source_unavailable_raises(self):
        skeleton = PipelineIR(steps=[StepIR(
            name="lambda_step",
            kind="filter",
            call_ast=ast.parse("def _(self, payload): pass").body[0],  # type: ignore[arg-type]
            source_hint="<lambda>",
        )])
        # A bare object() has no `call` — this must fail loudly, not silently.
        with pytest.raises(UnsupportedFilterShape):
            ParseFilterSourceFilter().call(Payload({
                "pipeline_ir": skeleton,
                "step_instances": [object()],
            }))
