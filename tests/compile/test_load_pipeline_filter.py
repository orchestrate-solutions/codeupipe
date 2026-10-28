"""RED tests for LoadPipelineFilter (M1)."""

import pytest

from codeupipe import Payload, Pipeline
from codeupipe.compile.errors import UnsupportedFilterShape
from codeupipe.compile.filters.load_pipeline_filter import LoadPipelineFilter
from codeupipe.compile.ir import PipelineIR


class _ExFilter:
    def call(self, payload):
        return payload.insert("k", 1)


class _ExTap:
    def observe(self, payload):
        pass


class _AlwaysTrue:
    def call(self, payload):
        return payload


class _Always:

    def test(self, payload):
        return True


class TestLoadPipeline:
    def test_extracts_step_labels_idents_and_kinds(self):
        p = Pipeline()
        p.add_filter(_ExFilter())
        p.add_tap(_ExTap())
        result = LoadPipelineFilter().call(Payload({"pipeline": p}))
        ir = result.get("pipeline_ir")
        assert isinstance(ir, PipelineIR)
        assert [s.name for s in ir.steps] == ["_ExFilter", "_ExTap"]
        assert [s.ident for s in ir.steps] == ["step_01_ex_filter", "step_02_ex_tap"]
        assert [s.kind for s in ir.steps] == ["filter", "tap"]

    def test_step_instances_are_aligned(self):
        p = Pipeline()
        p.add_filter(_ExFilter())
        p.add_filter(_ExFilter())
        result = LoadPipelineFilter().call(Payload({"pipeline": p}))
        instances = result.get("step_instances")
        assert len(instances) == 2
        assert all(isinstance(x, _ExFilter) for x in instances)

    def test_valve_is_detected_and_unwrapped(self):
        p = Pipeline()
        p.add_valve(_Always(), _AlwaysTrue())
        result = LoadPipelineFilter().call(Payload({"pipeline": p}))
        ir = result.get("pipeline_ir")
        assert ir.steps[0].kind == "valve"

