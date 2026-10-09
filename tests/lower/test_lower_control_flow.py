"""RED tests for LowerControlFlowFilter (M1)."""

import ast
import textwrap

from codeupipe import Payload
from codeupipe.lower.filters.lower_control_flow import LowerControlFlowFilter
from codeupipe.lower.ir import PipelineIR, StepIR


def _fn(src: str) -> ast.FunctionDef:
    return ast.parse(textwrap.dedent(src)).body[0]  # type: ignore[return-value]


class TestLowerControlFlow:
    def test_valve_predicate_is_dict_rewritten(self):
        call_fn = _fn("def gate(data):\n    return data")
        pred_fn = _fn("def _p(payload):\n    return payload.get('tier') == 'premium'")
        ir = PipelineIR(steps=[StepIR(
            name="gate",
            kind="valve",
            call_ast=call_fn,
            predicate_ast=pred_fn,
            source_hint="gate",
        )])
        result = LowerControlFlowFilter().call(Payload({"pipeline_ir": ir}))
        out = result.get("pipeline_ir")
        pred_src = ast.unparse(out.steps[0].predicate_ast)  # type: ignore[arg-type]
        assert "payload" not in pred_src
        assert "data.get" in pred_src

    def test_hooks_produce_warning_but_do_not_fail(self):
        from codeupipe.lower.ir import HookIR
        ir = PipelineIR(
            steps=[],
            hooks=[HookIR(name="metrics")],
        )
        result = LowerControlFlowFilter().call(Payload({"pipeline_ir": ir}))
        warnings = result.get("lowering_warnings") or []
        assert any("metrics" in w for w in warnings)
