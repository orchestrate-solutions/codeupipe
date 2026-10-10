"""
EmitInlineModuleFilter — the whole pipeline as one flattened ``run()``.

Direction: export (CUP -> standard Python), ``lowering="inline"``.

The fastest static mode: steps unrolled and inlined, no framework allocations.
Measured on the spike's P1 before building this (µs per run):

    current export (call + dict copy per step)   1.021
    calls kept, one copy + in-place writes       0.849
    inlined, copies kept                         0.941
    inlined + one copy + in-place writes         0.723   (hand-written: 0.728)

Only removing both costs reaches hand-written speed, so this does both:
``run()`` copies the caller's dict once, then each step's body runs inline
and writes keys in place.

A Payload write is in place, so a step's body is already in-place writes on
``data`` and can stand in ``run()`` as it is. A step is emitted as a function
and called instead when its shape cannot be pasted into ``run()``: an early
return, a nested function that closes over ``data``, a generator, or a step
that rebinds ``data``.
"""

from __future__ import annotations

import ast
import copy
import os
from typing import Dict, List, Set

from codeupipe.core import Payload

from ..errors import UnsupportedFilterShape


__all__ = ["EmitInlineModuleFilter"]


class EmitInlineModuleFilter:
    """Emit ``<base>/<step_dir>/pipeline.py`` holding one flattened ``run``."""

    def call(self, payload: Payload) -> Payload:
        pipeline_ir = payload.get("pipeline_ir")
        config = payload.get("config") or {"output": {"base": "src/", "step": "steps/"}}
        output = config.get("output", {})
        package_dir = os.path.join(output.get("base", "src/"), output.get("step", "steps/"))

        imports: Dict[str, str] = {}
        definitions: List[str] = []
        functions: List[str] = []
        body: List[str] = ["data = dict(data)"]

        for step in pipeline_ir.steps:
            prefix = f"_{step.ident}__"
            renames = _definition_renames(step, prefix)
            helpers: Dict[str, ast.FunctionDef] = {}
            for line in step.imports:
                _merge_import(imports, line, step)
            for source in step.definitions:
                tree = ast.parse(source)
                _rename_names(tree, renames)
                helpers.update({n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)})
                definitions.append(ast.unparse(tree))

            call_ast = _collapse_double_dict(_renamed_copy(step.call_ast, renames))
            if step.kind == "tap":
                body.extend(_tap_lines(step, call_ast, prefix, functions))
            elif step.kind == "valve":
                predicate = (_collapse_double_dict(_renamed_copy(step.predicate_ast, renames))
                             if step.predicate_ast else None)
                if predicate is None:
                    raise UnsupportedFilterShape(
                        filter_name=step.name, method_name="predicate", line=0, col=0,
                        node_kind="FunctionDef", suggestion="Valve reached the emitter without a predicate.",
                    )
                condition = _predicate_condition(predicate, prefix, functions, helpers)
                inner = _filter_lines(step, call_ast, prefix, functions)
                body.append(f"if {condition}:")
                body.extend(_indent(inner or ["pass"]))
            else:
                body.extend(_filter_lines(step, call_ast, prefix, functions))

        body.append("return data")
        sections = [
            "\n".join(sorted(imports.values())),
            "\n\n".join(definitions),
            "\n\n\n".join(functions),
            "def run(data):\n" + "\n".join(_indent(body)),
        ]
        module = "\n\n\n".join(section for section in sections if section) + "\n"

        files = list(payload.get("files") or [])
        files.append({"path": os.path.join(package_dir, "pipeline.py"), "content": module})
        files.append({"path": os.path.join(package_dir, "__init__.py"),
                      "content": "from .pipeline import run\n\n__all__ = [\"run\"]\n"})
        return payload.insert("files", files)


# --------------------------------------------------------------------------
# steps
# --------------------------------------------------------------------------

def _filter_lines(step, fn: ast.FunctionDef, prefix: str, functions: List[str]) -> List[str]:
    """Inline a filter body, or call it as a function."""
    if _inlinable(fn, allow_final_return=True):
        return _inline_filter(fn, prefix)
    functions.append(_as_function(fn, f"{prefix}step"))
    return [f"data = {prefix}step(data)"]


def _tap_lines(step, fn: ast.FunctionDef, prefix: str, functions: List[str]) -> List[str]:
    """Plane B: a Tap failure never halts the run (Exception only)."""
    if _inlinable(fn, allow_final_return=False):
        inner = [ast.unparse(stmt) for stmt in _body_without_docstring(_rename_locals(fn, prefix))]
    else:
        functions.append(_as_function(fn, f"{prefix}tap"))
        inner = [f"{prefix}tap(data)"]
    return ["try:", *_indent(inner or ["pass"]), "except Exception:", "    pass"]


def _indent(statements: List[str]) -> List[str]:
    """Indent every line; an unparsed compound statement spans several."""
    return ["    " + line for stmt in statements for line in stmt.splitlines()]


def _predicate_condition(fn: ast.FunctionDef, prefix: str, functions: List[str],
                         helpers: Dict[str, ast.FunctionDef]) -> str:
    body = _body_without_docstring(fn)
    if len(body) == 1 and isinstance(body[0], ast.Return) and body[0].value is not None:
        return ast.unparse(_inline_helper_call(body[0].value, helpers))
    functions.append(_as_function(fn, f"{prefix}predicate"))
    return f"{prefix}predicate(data)"


def _inline_filter(fn: ast.FunctionDef, prefix: str) -> List[str]:
    fn = _rename_locals(fn, prefix)
    statements = _body_without_docstring(fn)
    *head, last = statements
    lines = [ast.unparse(stmt) for stmt in head]
    value = last.value
    if isinstance(value, ast.Name) and value.id == "data":
        return lines
    return lines + [f"data = {ast.unparse(value)}"]


# --------------------------------------------------------------------------
# redundant copies
# --------------------------------------------------------------------------

class _CollapseDoubleDict(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call):
        node = self.generic_visit(node)
        if _is_dict_call(node) and _is_dict_call(node.args[0]):
            return node.args[0]
        return node


def _is_dict_call(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict"
            and len(node.args) == 1 and not node.keywords)


def _collapse_double_dict(fn: ast.AST) -> ast.AST:
    """``dict(dict(x))`` is ``dict(x)``."""
    return ast.fix_missing_locations(_CollapseDoubleDict().visit(fn))


def _inline_helper_call(expr: ast.AST, helpers: Dict[str, ast.FunctionDef]) -> ast.AST:
    """``helper(dict(data))`` -> the helper's return expression over ``data``,
    when the helper is ``def helper(d): return <expr>`` and only reads ``d``
    through ``d.get(...)``. Generated adapters wrap Valve predicates this
    way, copying the whole dict on each check."""
    if not (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and len(expr.args) == 1
            and not expr.keywords and _is_dict_call(expr.args[0])
            and isinstance(expr.args[0].args[0], ast.Name) and expr.args[0].args[0].id == "data"):
        return expr
    helper = helpers.get(expr.func.id)
    if helper is None or len(helper.args.args) != 1 or helper.args.vararg or helper.args.kwarg:
        return expr
    body = _body_without_docstring(helper)
    if not (len(body) == 1 and isinstance(body[0], ast.Return) and body[0].value is not None):
        return expr
    param = helper.args.args[0].arg
    returned = copy.deepcopy(body[0].value)
    parents = {child: parent for parent in ast.walk(returned) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(returned):
        if isinstance(node, ast.Name) and node.id == param:
            parent = parents.get(node)
            if not (isinstance(parent, ast.Attribute) and parent.attr == "get"
                    and isinstance(parents.get(parent), ast.Call)):
                return expr
            node.id = "data"
        elif isinstance(node, (ast.Lambda, ast.NamedExpr)):
            return expr
    return returned


# --------------------------------------------------------------------------
# inlinability: can `data` escape this body?
# --------------------------------------------------------------------------

def _inlinable(fn: ast.FunctionDef, allow_final_return: bool, any_return: bool = False) -> bool:
    body = _body_without_docstring(fn)
    if not body:
        return not allow_final_return
    for node in ast.walk(fn):
        if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await, ast.Global, ast.Nonlocal)):
            return False
        if isinstance(node, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not fn:
            if any(isinstance(n, ast.Name) and n.id == "data" for n in ast.walk(node)):
                return False
        if isinstance(node, ast.Name) and node.id == "data" and not isinstance(node.ctx, ast.Load):
            return False
    returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
    final = body[-1] if isinstance(body[-1], ast.Return) else None
    if any_return:
        pass
    elif allow_final_return:
        if final is None or final.value is None or returns != [final]:
            return False
    elif returns:
        return False
    return True


# --------------------------------------------------------------------------
# names
# --------------------------------------------------------------------------

def _definition_renames(step, prefix: str) -> Dict[str, str]:
    renames: Dict[str, str] = {}
    for source in step.definitions:
        for stmt in ast.parse(source).body:
            for name in _top_level_bound(stmt):
                renames[name] = prefix + name
    return renames


def _top_level_bound(stmt: ast.stmt) -> Set[str]:
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {stmt.name}
    names: Set[str] = set()
    targets = stmt.targets if isinstance(stmt, ast.Assign) else [getattr(stmt, "target", None)]
    for target in targets:
        for node in ast.walk(target) if target is not None else ():
            if isinstance(node, ast.Name):
                names.add(node.id)
    return names


def _rename_names(tree: ast.AST, renames: Dict[str, str]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in renames:
            node.id = renames[node.id]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in renames:
            node.name = renames[node.name]


def _renamed_copy(fn: ast.AST, renames: Dict[str, str]) -> ast.AST:
    fn = copy.deepcopy(fn)
    _rename_names(fn, renames)
    return fn


def _rename_locals(fn: ast.FunctionDef, prefix: str) -> ast.FunctionDef:
    """Prefix every name the body binds, so inlined steps cannot collide."""
    fn = copy.deepcopy(fn)
    local: Set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            local.add(node.id)
        elif isinstance(node, ast.arg) and node is not fn.args.args[0]:
            local.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            local.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not fn:
            local.add(node.name)
    local.discard("data")
    renames = {name: prefix + name for name in local}
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and node.id in renames:
            node.id = renames[node.id]
        elif isinstance(node, ast.arg) and node.arg in renames:
            node.arg = renames[node.arg]
        elif isinstance(node, ast.ExceptHandler) and node.name in renames:
            node.name = renames[node.name]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not fn:
            node.name = renames.get(node.name, node.name)
    return fn


def _body_without_docstring(fn: ast.FunctionDef) -> List[ast.stmt]:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def _as_function(fn: ast.FunctionDef, name: str) -> str:
    fn = copy.deepcopy(fn)
    fn.name = name
    return ast.unparse(fn)


def _merge_import(imports: Dict[str, str], line: str, step) -> None:
    bound = _top_level_bound_import(line)
    for name in bound:
        existing = imports.get(name)
        if existing is not None and existing != line:
            raise UnsupportedFilterShape(
                filter_name=step.name, method_name="imports", line=0, col=0, node_kind="Import",
                suggestion=f"`{name}` is imported differently by two steps ({existing!r} vs {line!r}); "
                           "use the default per-step lowering for this pipeline.",
            )
        imports[name] = line


def _top_level_bound_import(line: str) -> Set[str]:
    stmt = ast.parse(line).body[0]
    if isinstance(stmt, ast.Import):
        return {alias.asname or alias.name.split(".")[0] for alias in stmt.names}
    return {alias.asname or alias.name for alias in stmt.names}
