"""
LowerControlFlowFilter — Valve/Tap control flow lowered to plain Python.

Direction: export (CUP -> standard Python).
Milestone: M1.
"""

from __future__ import annotations

import ast
from dataclasses import replace

from codeupipe.core import Payload

from .rewrite_payload_ops_filter import RewritePayloadOpsFilter, _PayloadToDictTransformer


__all__ = ["LowerControlFlowFilter"]


class LowerControlFlowFilter:
    """Convert Valve/Tap semantics into orchestrator-friendly IR annotations."""

    def call(self, payload: Payload) -> Payload:
        pipeline_ir = payload.get("pipeline_ir")
        rewritten_steps = []

        for step in pipeline_ir.steps:
            predicate_ast = step.predicate_ast
            if predicate_ast is not None:
                name = getattr(predicate_ast, "name", "predicate")
                transformer = _PayloadToDictTransformer(
                    step.name, name, step.ident, RewritePayloadOpsFilter.payload_parameter(predicate_ast, after_self=False))
                predicate_ast = ast.fix_missing_locations(
                    transformer.visit(ast.parse(ast.unparse(predicate_ast)).body[0])
                )
            rewritten_steps.append(replace(step, predicate_ast=predicate_ast))

        result = payload.insert("pipeline_ir", replace(pipeline_ir, steps=rewritten_steps))
        if pipeline_ir.hooks:
            warnings = [f"Hook lowering deferred to M4: {hook.name}" for hook in pipeline_ir.hooks]
            result = result.insert("lowering_warnings", warnings)
        return result
