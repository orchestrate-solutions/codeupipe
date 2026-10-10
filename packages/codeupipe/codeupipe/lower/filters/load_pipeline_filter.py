"""
LoadPipelineFilter — live CUP Pipeline instance -> PipelineIR skeleton.

Direction: export (CUP -> standard Python).
Milestone: M1.
"""

from __future__ import annotations

import ast
import inspect
import re

from codeupipe.core import Payload
from codeupipe.core.valve import Valve

from ..errors import UnsupportedFilterShape
from ..ir import PipelineIR, PipelineMeta, StepIR


__all__ = ["LoadPipelineFilter"]


_PLACEHOLDER_AST = ast.parse("def placeholder(payload):\n    return payload").body[0]


def _refuse(name: str, node_kind: str, suggestion: str) -> UnsupportedFilterShape:
    return UnsupportedFilterShape(filter_name=name, method_name="call", line=0, col=0,
                                  node_kind=node_kind, suggestion=suggestion)


def _check_pipeline(pipeline, name: str, allow_hooks: bool = False) -> None:
    """Refuse a pipeline whose behaviour static code cannot reproduce.

    ``allow_hooks``: observable export (``observe=True``) calls the top-level
    pipeline's Hooks. Hooks on a nested pipeline stay refused: its hooks are
    objects owned by that inner run, which the flattened code does not have.
    """
    if not hasattr(pipeline, "_steps"):
        raise _refuse(name, type(pipeline).__name__,
                      "Export takes a Pipeline. This object wraps one or is not one.")
    if getattr(pipeline, "_hooks", None) and not allow_hooks:
        raise _refuse(name, "Hook",
                      "Hooks do not run in the fast static export. Export with observe=True "
                      "(top-level Hooks only), or remove them.")


def _ident(index: int, label: str) -> str:
    """A safe, readable Python identifier for a step: ``step_03_validate``.

    Generated code never uses the label itself as a name: it is a string
    (``Validate#2``), and anything derived from user code could
    collide with a builtin, a module global or the generated run().
    """
    short = label.rsplit("/", 1)[-1].split("#", 1)[0].rsplit(".", 1)[-1]
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", short).lower()
    snake = re.sub(r"\W+", "_", snake).strip("_") or "step"
    return f"step_{index:02d}_{snake}"


def _is_async(fn) -> bool:
    return inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)


def _flatten(steps, prefix="", group=None):
    """Expand nested pipelines into their steps, in order.

    A nested pipeline runs its steps in sequence on the parent's payload, so
    lowering it as those steps inline is the same computation. Names get the
    nesting step's name as a prefix (``inner__greet``) so they stay unique
    and remain unique. Each step also carries ``group``, the
    top-level step it came from, so observable export can still report the
    nested pipeline as one step.
    """
    for name, instance, step_type in steps:
        if step_type == "pipeline":
            _check_pipeline(instance, f"{prefix}{name}")
            yield from _flatten(instance._steps, f"{prefix}{name}/", group or name)
        else:
            yield f"{prefix}{name}", instance, step_type, group


def _refuse_empty_nested(steps) -> None:
    """A nested pipeline that flattens to no steps leaves nothing for the
    observable export to hang its State entry and Hook calls on, while the
    dynamic run still reports it as executed. Refuse rather than drop it."""
    for name, instance, step_type in steps:
        if step_type == "pipeline" and not any(True for _ in _flatten(instance._steps)):
            raise _refuse(name, "EmptyPipeline",
                          "A nested pipeline with no steps cannot be reported in State and Hooks "
                          "by observable export. Remove it, or export without observe=True.")


class LoadPipelineFilter:
    """Introspect ``Pipeline._steps`` / ``._hooks`` into a skeleton IR."""

    def call(self, payload: Payload) -> Payload:
        pipeline = payload.get("pipeline")
        pattern = payload.get("pattern", "flat")
        observe = bool(payload.get("observe", False))
        if observe and payload.get("lowering") == "inline":
            raise ValueError("observe=True needs the per-step layout: the inline layout writes the "
                             "payload in place, so Hooks would see later steps' writes. Use "
                             "lowering='steps' (the default) to observe.")
        _check_pipeline(pipeline, "<pipeline>", allow_hooks=observe)
        if observe:
            _refuse_empty_nested(pipeline._steps)
        steps = []
        step_instances = []
        step_predicates = []

        for name, instance, step_type, group in _flatten(pipeline._steps):
            kind = None
            source_instance = instance
            predicate = None
            if isinstance(instance, Valve):
                kind = "valve"
                source_instance = instance._inner
                predicate = instance._predicate_object
            elif step_type in {"filter", "async_filter"}:
                kind = "filter"
            elif step_type in {"tap", "async_tap"}:
                kind = "tap"
            else:
                raise UnsupportedFilterShape(
                    filter_name=name,
                    method_name="call",
                    line=0,
                    col=0,
                    node_kind=step_type,
                    suggestion="Only filter, tap, and valve steps are exportable in M1.",
                )

            method = getattr(source_instance, "observe" if kind == "tap" else "call", None)
            if _is_async(method):
                raise _refuse(name, "AsyncFunctionDef",
                              "Static run() is sync, as the dynamic run() is (it raises "
                              "AsyncStepInSyncRun here). Make the step sync to export it.")

            steps.append(
                StepIR(
                    name=name,
                    kind=kind,
                    call_ast=ast.parse(ast.unparse(_PLACEHOLDER_AST)).body[0],
                    source_hint=source_instance.__class__.__name__,
                    group=group,
                    ident=_ident(len(steps) + 1, name),
                )
            )
            step_instances.append(source_instance)
            step_predicates.append(predicate)

        pipeline_ir = PipelineIR(steps=steps, meta=PipelineMeta(pattern=pattern, source_hint="cup"))
        result = (
            payload.insert("pipeline_ir", pipeline_ir)
            .insert("step_instances", step_instances)
            .insert("step_predicates", step_predicates)
            .insert("source_hooks", tuple(type(h).__name__ for h in getattr(pipeline, "_hooks", ())))
        )
        return result
