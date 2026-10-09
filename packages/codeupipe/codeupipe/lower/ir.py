"""
Pipeline IR — the shared intermediate representation for converter v2.

Both directions (CUP -> plain-Python, plain-Python -> CUP) read and write
this same IR. Keeping it as the single source of truth is what makes the
round-trip contract enforceable.

Design notes:
    * ``call_ast`` is an ``ast.FunctionDef`` — NOT a source string. Emitters
      use ``ast.unparse`` when they need text. This eliminates whole classes
      of formatting-drift bugs.
    * The IR is intentionally small. Any concept not captured here is
      out-of-scope for the v1 MVP. Additions require a plan update.
    * Frozen dataclasses — the IR is data, not state. Rewriters produce new
      IR nodes rather than mutating in place.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


__all__ = [
    "StepKind",
    "SourceHint",
    "Pattern",
    "ContractPrimitive",
    "DataFlowEventKind",
    "PipelineMeta",
    "PrimitiveContractIR",
    "DataFlowEventIR",
    "SymbolFlowShapeIR",
    "StepIR",
    "HookIR",
    "PipelineIR",
]


StepKind = Literal["filter", "valve", "tap"]
ContractPrimitive = Literal["payload", "filter", "valve", "tap", "hook", "pipeline", "state", "unknown"]
DataFlowEventKind = Literal["set", "read"]
SourceHint = Literal["cup", "standard"]
Pattern = Literal["flat", "mvc", "clean", "hexagonal"]


@dataclass(frozen=True)
class PipelineMeta:
    """Provenance and target-layout hints carried alongside the IR."""

    pattern: Pattern = "flat"
    source_hint: SourceHint = "cup"


@dataclass(frozen=True)
class PrimitiveContractIR:
    """Language-agnostic primitive assignment for a discovered symbol."""

    module_ref: str
    symbol: str
    symbol_kind: Literal["function", "class"]
    primitive: ContractPrimitive
    confidence: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DataFlowEventIR:
    """Abstract data-flow event observed within a symbol body."""

    module_ref: str
    symbol: str
    event: DataFlowEventKind
    key: str
    index: int
    conditional: bool = False


@dataclass(frozen=True)
class SymbolFlowShapeIR:
    """Per-symbol abstract shape summary for set/read contracts."""

    module_ref: str
    symbol: str
    keys_set: List[str] = field(default_factory=list)
    keys_read: List[str] = field(default_factory=list)
    keys_reassigned: List[str] = field(default_factory=list)
    conditionally_set_keys: List[str] = field(default_factory=list)
    reads_before_any_set: List[str] = field(default_factory=list)
    reads_before_unconditional_set: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class StepIR:
    """A single pipeline step in canonical form.

    Attributes:
        name: The step's name as it appears in ``Pipeline.add_filter(name=...)``.
        kind: ``"filter"`` | ``"valve"`` | ``"tap"``.
        call_ast: The rewritten body as an ``ast.FunctionDef`` whose parameter
            is named ``data`` (never ``payload``). This is the canonical shape
            emitters lower to plain Python.
        predicate_ast: Only populated when ``kind == "valve"``. Lambda or
            FunctionDef whose parameter is ``data``.
        docstring: The original ``call`` method docstring, preserved for
            downstream emitters.
        source_hint: The original class or function name (for diagnostics
            and for emitters that want to preserve names).
        imports: Import lines the step needs, sorted.
        definitions: Top-level statements copied from the step's defining
            module (constants, helpers, classes), in source order, so the
            emitted file runs without that module.
        ident: The Python identifier the generated code uses for this step's
            module and function (``step_03_validate``). Generated, never taken
            from ``name``: ``name`` is the step's identity (a label such as
            ``app.filters.Validate#2``), which is not an identifier.
        group: For a step flattened out of a nested Pipeline, the name of the
            top-level step that nested it (``inner`` for ``inner__greet``).
            Observable export uses it to report the nested pipeline as one
            step, as the dynamic run does. ``None`` for top-level steps.
        test_spec: Structured testing hints gathered during detection. This is
            deliberately lightweight dict data so generators can deepen test
            quality without re-parsing emitted code.
    """

    name: str
    kind: StepKind
    call_ast: ast.FunctionDef
    predicate_ast: Optional[ast.AST] = None
    docstring: Optional[str] = None
    source_hint: Optional[str] = None
    imports: tuple = ()
    definitions: tuple = ()
    test_spec: Dict[str, Any] = field(default_factory=dict)
    group: Optional[str] = None
    ident: str = ""

    def __post_init__(self):
        # IR built by hand (tests, the import direction) names steps with
        # identifiers already; default ``ident`` to that name.
        if not self.ident:
            object.__setattr__(self, "ident", self.name)


@dataclass(frozen=True)
class HookIR:
    """A pipeline-wide lifecycle hook in canonical form.

    v1 MVP does not fully lower Hooks; this shape exists so M4 work can
    slot in without changing the IR contract.
    """

    name: str
    before_ast: Optional[ast.FunctionDef] = None
    after_ast: Optional[ast.FunctionDef] = None
    on_error_ast: Optional[ast.FunctionDef] = None


@dataclass(frozen=True)
class PipelineIR:
    """The full canonical representation of a pipeline."""

    steps: List[StepIR] = field(default_factory=list)
    hooks: List[HookIR] = field(default_factory=list)
    meta: PipelineMeta = field(default_factory=PipelineMeta)
    test_spec: Dict[str, Any] = field(default_factory=dict)
