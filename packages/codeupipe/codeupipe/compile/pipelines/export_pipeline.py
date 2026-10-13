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


__all__ = ["ExportPipeline", "build_export_pipeline_v2"]


class ExportPipeline(Pipeline):
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

    def __init__(self, *, write: bool = True):
        super().__init__()
        self.add_filter(LoadPipelineFilter())
        self.add_filter(ParseFilterSourceFilter())
        self.add_filter(RewritePayloadOpsFilter())
        self.add_filter(LowerControlFlowFilter())
        self.add_valve(LoweringModePredicate(inline=False), EmitPlainFilesFilter())
        self.add_valve(LoweringModePredicate(inline=False), EmitOrchestratorFilter())
        self.add_valve(LoweringModePredicate(inline=True), EmitInlineModuleFilter())
        if write:
            self.add_tap(WriteFilesTap())


def build_export_pipeline_v2(*, write: bool = True) -> Pipeline:
    """The export pipeline. Kept for callers that used this name: see ``ExportPipeline``."""
    return ExportPipeline(write=write)
