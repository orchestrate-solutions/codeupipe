"""
EmitPlainFilesFilter — PipelineIR steps -> one plain-Python file each.

Direction: export (CUP -> standard Python).
Milestone: M1.
"""

from __future__ import annotations

import ast
import os

from codeupipe.core import Payload


__all__ = ["EmitPlainFilesFilter"]


def _default_config(payload: Payload):
    return payload.get("config") or {
        "pattern": payload.get("pattern", "flat"),
        "output": {"base": "src/", "step": "steps/"},
    }


class EmitPlainFilesFilter:
    """Render each ``StepIR.call_ast`` to a standalone .py file."""

    def call(self, payload: Payload) -> Payload:
        pipeline_ir = payload.get("pipeline_ir")
        config = _default_config(payload)
        output = config.get("output", {})
        base = output.get("base", "src/")
        step_dir = output.get("step", "steps/")
        files = list(payload.get("files") or [])

        for step in pipeline_ir.steps:
            imports = tuple(getattr(step, "imports", ()) or ())
            definitions = [ast.parse(d) for d in (getattr(step, "definitions", ()) or ())]
            call_ast = ast.parse(ast.unparse(step.call_ast)).body[0]
            predicate = None
            if step.kind == "valve" and step.predicate_ast is not None:
                predicate = ast.parse(ast.unparse(step.predicate_ast)).body[0]
                # The orchestrator imports ``<step>_predicate``. A copied helper
                # can already own that name (generated code wraps a dict
                # predicate of exactly that name), and the Valve predicate
                # would then call itself. Move the helper aside instead.
                wanted = f"{step.ident}_predicate"
                if any(wanted in _bound_names(tree) for tree in definitions):
                    moved = _unused_name(f"{wanted}_impl", definitions)
                    for tree in [*definitions, call_ast, predicate]:
                        _rename(tree, wanted, moved)
                if isinstance(predicate, ast.FunctionDef):
                    predicate.name = wanted

            header = ""
            if imports:
                header = "\n".join(imports) + "\n\n"
            if definitions:
                header += "\n\n".join(ast.unparse(tree) for tree in definitions) + "\n\n\n"

            content = header + ast.unparse(call_ast) + "\n"
            if predicate is not None:
                content += "\n" + ast.unparse(predicate) + "\n"
            files.append({
                "path": os.path.join(base, step_dir, f"{step.ident}.py"),
                "content": content,
            })

        return payload.insert("files", files)


def _bound_names(tree: ast.AST) -> set:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    return names


def _unused_name(candidate: str, trees) -> str:
    taken = set().union(*(_bound_names(t) for t in trees)) if trees else set()
    name, n = candidate, 2
    while name in taken:
        name, n = f"{candidate}{n}", n + 1
    return name


def _rename(tree: ast.AST, old: str, new: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == old:
            node.id = new
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == old:
            node.name = new
