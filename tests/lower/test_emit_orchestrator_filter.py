"""RED tests for EmitOrchestratorFilter (M1)."""

import ast
import textwrap

from codeupipe import Payload
from codeupipe.lower.filters.emit_orchestrator_filter import EmitOrchestratorFilter
from codeupipe.lower.ir import PipelineIR, StepIR


def _plain_fn(name: str) -> ast.FunctionDef:
    return ast.parse(textwrap.dedent(f"""
        def {name}(data):
            return data
    """)).body[0]  # type: ignore[return-value]


class TestEmitOrchestrator:
    def test_orchestrator_calls_steps_in_order(self):
        ir = PipelineIR(steps=[
            StepIR(name="first",  kind="filter", call_ast=_plain_fn("first"),  source_hint="first"),
            StepIR(name="second", kind="filter", call_ast=_plain_fn("second"), source_hint="second"),
            StepIR(name="third",  kind="filter", call_ast=_plain_fn("third"),  source_hint="third"),
        ])
        result = EmitOrchestratorFilter().call(Payload({
            "pipeline_ir": ir,
            "config": {"pattern": "flat", "output": {"base": "src/", "step": "steps/"}},
            "files": [],
        }))
        files = result.get("files")
        orch = next(f for f in files if f["path"].endswith("pipeline.py"))
        # The three calls appear in insertion order.
        i1 = orch["content"].find("first")
        i2 = orch["content"].find("second")
        i3 = orch["content"].find("third")
        assert 0 <= i1 < i2 < i3

    def test_tap_emits_bare_call_no_assignment(self):
        ir = PipelineIR(steps=[
            StepIR(name="log",  kind="tap",    call_ast=_plain_fn("log"),  source_hint="log"),
            StepIR(name="work", kind="filter", call_ast=_plain_fn("work"), source_hint="work"),
        ])
        result = EmitOrchestratorFilter().call(Payload({
            "pipeline_ir": ir,
            "config": {"pattern": "flat", "output": {"base": "src/", "step": "steps/"}},
            "files": [],
        }))
        orch = next(f for f in result.get("files") if f["path"].endswith("pipeline.py"))
        # Taps do not appear on the left-hand side of an assignment.
        assert "= log(" not in orch["content"]
        assert "= work(" in orch["content"]
