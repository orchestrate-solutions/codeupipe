"""
Export pipeline: CUP Pipeline instance -> plain-Python package on disk.

Milestone: M1 (wire).
"""

from __future__ import annotations

from codeupipe.core import Pipeline

from ..filters.load_pipeline_filter import LoadPipelineFilter
from ..filters.parse_filter_source_filter import ParseFilterSourceFilter
from ..filters.rewrite_payload_ops_filter import RewritePayloadOpsFilter
from ..filters.lower_control_flow_filter import LowerControlFlowFilter
from ..filters.emit_plain_files_filter import EmitPlainFilesFilter
from ..filters.emit_orchestrator_filter import EmitOrchestratorFilter
from ..filters.emit_inline_module_filter import EmitInlineModuleFilter
from ..taps.write_files_tap import WriteFilesTap
from .lowering_mode_predicate import LoweringModePredicate


__all__ = ["build_export_pipeline_v2"]


def build_export_pipeline_v2(*, write: bool = True) -> Pipeline:
    """Assemble the v2 export pipeline.

    Args:
        write: If True, adds the ``WriteFilesTap`` at the end so
            emitted files land on disk. Set False for tests that
            only want the ``files`` payload in memory.

    Input payload keys:
        ``pipeline``     (Pipeline)     — the CUP instance to export.
        ``pattern``      (str)          — layout pattern; defaults to "flat".
        ``output_dir``   (str)          — root for WriteFilesTap.
        ``lowering``     (str)          — "steps" (default): one module per
                                          step plus an orchestrator.
                                          "inline": one flattened ``run()``
                                          with in-place writes (static mode).
        ``observe``      (bool)         — False (default): run(data), no
                                          State or Hooks. True: run() also
                                          records State and calls Hooks as
                                          the dynamic run does; "steps"
                                          layout only. docs/compile.md

    Output payload keys:
        ``pipeline_ir``  (PipelineIR)   — the canonical IR.
        ``files``        (list[dict])   — the emitted files.
    """
    p = Pipeline()
    p.add_filter(LoadPipelineFilter())
    p.add_filter(ParseFilterSourceFilter())
    p.add_filter(RewritePayloadOpsFilter())
    p.add_filter(LowerControlFlowFilter())
    p.add_valve(LoweringModePredicate(inline=False), EmitPlainFilesFilter())
    p.add_valve(LoweringModePredicate(inline=False), EmitOrchestratorFilter())
    p.add_valve(LoweringModePredicate(inline=True), EmitInlineModuleFilter())
    if write:
        p.add_tap(WriteFilesTap())
    return p
