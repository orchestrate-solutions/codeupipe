"""
ParseFilterSourceFilter — extract each Filter's ``call`` method as an AST.

Direction: export (CUP -> standard Python).
Milestone: M0.
"""

from __future__ import annotations

import ast
import builtins
import inspect
import sys
import textwrap
import types
from dataclasses import replace
from typing import Iterable, Optional, Tuple

from codeupipe.core import Payload

from ..errors import UnsupportedFilterShape


__all__ = ["ParseFilterSourceFilter"]


_BUILTIN_NAMES = frozenset(dir(builtins))


class ParseFilterSourceFilter:
    """Turn each step's live instance into an ``ast.FunctionDef``."""

    def call(self, payload: Payload) -> Payload:
        pipeline_ir = payload.get("pipeline_ir")
        step_instances = payload.get("step_instances") or []
        step_predicates = payload.get("step_predicates") or [None] * len(step_instances)
        rewritten_steps = []

        for step, instance, predicate in zip(pipeline_ir.steps, step_instances, step_predicates):
            method_name = "observe" if step.kind == "tap" else "call"
            method = getattr(instance, method_name, None)
            if method is None:
                raise UnsupportedFilterShape(
                    filter_name=step.name,
                    method_name=method_name,
                    line=getattr(step.call_ast, "lineno", 0),
                    col=getattr(step.call_ast, "col_offset", 0),
                    node_kind="Attribute",
                    suggestion="Define the step in a real .py file with a concrete call/observe method.",
                )
            try:
                source = textwrap.dedent(inspect.getsource(method))
            except (OSError, TypeError):
                raise UnsupportedFilterShape(
                    filter_name=step.name,
                    method_name=method_name,
                    line=getattr(step.call_ast, "lineno", 0),
                    col=getattr(step.call_ast, "col_offset", 0),
                    node_kind="FunctionDef",
                    suggestion="Define the step in a real .py file so inspect.getsource can recover it.",
                )
            function_ast = _erase_annotations(ast.parse(source).body[0])
            function_ast, config = _bind_instance_config(function_ast, instance, step)
            imports, definitions = _detect_dependencies(function_ast, method, step.name)
            definitions = config + definitions
            predicate_ast = None
            if step.kind == "valve":
                predicate_ast, p_config = _parse_predicate(step, predicate)
                p_imports, p_definitions = _detect_dependencies(predicate_ast, predicate.test, step.name)
                imports = tuple(sorted(set(imports) | set(p_imports)))
                p_definitions = p_config + p_definitions
                definitions = definitions + tuple(d for d in p_definitions if d not in definitions)
            rewritten_steps.append(
                replace(
                    step,
                    call_ast=function_ast,
                    docstring=ast.get_docstring(function_ast),
                    imports=imports,
                    definitions=definitions,
                    predicate_ast=predicate_ast,
                )
            )

        return payload.insert("pipeline_ir", replace(pipeline_ir, steps=rewritten_steps))


class _EraseAnnotations(ast.NodeTransformer):
    """Drop every type hint in a function: on its parameters, its return, and
    its locals (``x: T = v`` becomes ``x = v``; a bare ``x: T`` goes)."""

    def _function(self, node):
        node.returns = None
        arguments = node.args
        for argument in arguments.posonlyargs + arguments.args + arguments.kwonlyargs:
            argument.annotation = None
        for argument in (arguments.vararg, arguments.kwarg):
            if argument is not None:
                argument.annotation = None
        return self.generic_visit(node)

    visit_FunctionDef = visit_AsyncFunctionDef = _function

    def generic_visit(self, node):
        node = super().generic_visit(node)
        # A block whose only statement was a bare hint must not be left empty.
        if isinstance(getattr(node, "body", None), list) and not node.body:
            node.body = [ast.Pass()]
        return node

    def visit_AnnAssign(self, node):
        if node.value is None:
            return None
        return ast.copy_location(ast.Assign(targets=[node.target], value=self.visit(node.value)), node)


def _erase_annotations(fn):
    """A step's type hints say what it reads and writes; they are for the
    author and the tools, as in TypeScript. Exported code carries none, so it
    never refers to the hint's names (``Payload``, a TypedDict) and so never
    imports the framework."""
    return ast.fix_missing_locations(_EraseAnnotations().visit(fn))


def _bind_instance_config(fn: ast.FunctionDef, instance, step, prefix: str = "_self_") -> Tuple[ast.FunctionDef, tuple]:
    """Compile a step's constructor config into it as named constants.

    Export lowers a *live* Pipeline, so each ``self.<attr>`` the method reads
    already has its value. A value with a literal form is baked in as
    ``_self_<attr> = <literal>`` — per step, so two instances of one class
    keep their own config. Anything that cannot be compiled in is refused
    here rather than left as a reference to a ``self`` that will not exist.
    """
    if not fn.args.args:
        return fn, ()
    self_name = fn.args.args[0].arg
    constants: dict = {}

    def refuse(attr: str, why: str, node: ast.AST) -> UnsupportedFilterShape:
        return UnsupportedFilterShape(
            filter_name=step.name,
            method_name=fn.name,
            line=getattr(node, "lineno", 0),
            col=getattr(node, "col_offset", 0),
            node_kind="Attribute",
            suggestion=f"`{self_name}.{attr}` {why}",
        )

    class _Bind(ast.NodeTransformer):
        def visit_Attribute(self, node: ast.Attribute):
            if not (isinstance(node.value, ast.Name) and node.value.id == self_name):
                return self.generic_visit(node)
            attr = node.attr
            if not isinstance(node.ctx, ast.Load):
                raise refuse(attr, "is written inside the step; per-instance state has no static form.", node)
            if attr not in constants:
                if not hasattr(instance, attr):
                    raise refuse(attr, "is not set on the instance being exported.", node)
                value = getattr(instance, attr)
                if callable(value):
                    raise refuse(attr, "is a method or callable; inline it, or make it a module-level function.", node)
                literal = _literal_source(value)
                if literal is None:
                    raise refuse(attr, f"holds a {type(value).__name__}, which has no literal form to compile in.", node)
                constants[attr] = (f"{prefix}{attr}", literal)
            return ast.copy_location(ast.Name(id=constants[attr][0], ctx=ast.Load()), node)

        def visit_Name(self, node: ast.Name):
            if node.id == self_name:
                raise refuse("", f"`{self_name}` is used directly; only reads of literal attributes can be compiled in.", node)
            return node

    body = [_Bind().visit(stmt) for stmt in fn.body]
    fn.body = [ast.fix_missing_locations(stmt) for stmt in body]
    definitions = tuple(f"{name} = {literal}" for name, literal in constants.values())
    return fn, definitions


def _literal_source(value) -> Optional[str]:
    """``repr(value)`` if it evaluates back to an equal value of the same type."""
    source = repr(value)
    try:
        back = ast.literal_eval(source)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None
    if type(back) is not type(value) or back != value:
        return None
    return source


def _parse_predicate(step, predicate) -> Tuple[ast.FunctionDef, tuple]:
    """Recover a Valve predicate object's ``test`` as a ``def`` taking ``payload``.

    Predicates are objects (conformance/API.md, "Valve"): the ``test``
    method is lowered like a filter's ``call``, the instance's literal
    settings compiled in as constants (``_when_<attr>``, so they cannot
    collide with the filter's ``_self_<attr>`` in the same module). The
    orchestrator always emits ``if <step>_predicate(data):``, so a predicate
    that cannot be recovered stops the export here.
    """
    def refuse(suggestion: str, kind: str = "FunctionDef") -> UnsupportedFilterShape:
        return UnsupportedFilterShape(
            filter_name=step.name, method_name="predicate", line=0, col=0, node_kind=kind, suggestion=suggestion,
        )

    method = getattr(predicate, "test", None)
    if method is None:
        raise refuse("A Valve predicate is an object with test(self, payload) -> bool.")
    try:
        fn = _erase_annotations(ast.parse(textwrap.dedent(inspect.getsource(method))).body[0])
    except (OSError, TypeError, SyntaxError, IndexError):
        raise refuse("Define the predicate class in a real .py file so inspect.getsource can recover it.")
    if not isinstance(fn, ast.FunctionDef) or len(fn.args.args) != 2:
        raise refuse("A Valve predicate's test must be a plain `def test(self, payload)`.")
    fn, config = _bind_instance_config(fn, predicate, step, prefix="_when_")
    fn.args.args = fn.args.args[1:]  # self is gone: its reads are now constants
    return _rename_parameter(fn, fn.args.args[0].arg, "payload"), config


def _rename_parameter(fn: ast.FunctionDef, old: str, new: str) -> ast.FunctionDef:
    """Rename the predicate's parameter so RewritePayloadOps recognises it."""
    if old == new:
        return fn
    fn.args.args[0].arg = new
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and node.id == old:
            node.id = new
    return fn


def _detect_dependencies(fn: ast.FunctionDef, obj, step_name: str) -> Tuple[tuple, tuple]:
    """Return ``(imports, definitions)`` the step body needs to run standalone.

    Names are resolved against the defining module's *source* first, because
    that is what the author wrote: a top-level import is re-emitted as that
    import, and a top-level constant, helper, or class is copied verbatim
    (with whatever it needs in turn). Only names the source does not bind
    fall back to runtime introspection of the value.

    Resolving by value alone is what dropped same-module constants and
    turned ``_WORDS = re.compile(...)`` into ``from re import _WORDS``: a
    compiled pattern reports ``__module__ == "re"``. A name that neither
    route can place raises instead of being dropped.
    """
    module = inspect.getmodule(obj)
    if module is None:
        return (), ()
    module_ns = getattr(module, "__dict__", {})
    if not module_ns:
        return (), ()
    bindings = _module_bindings(module)

    imports: set = set()
    definitions: dict = {}
    pending = list(_referenced_free_names(fn, _local_names(fn)))
    seen: set = set()
    while pending:
        name = pending.pop()
        if name in seen or name in _BUILTIN_NAMES:
            continue
        seen.add(name)

        stmt = bindings.get(name)
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            import_line = _import_line_for_alias(stmt, name)
            if import_line is not None:
                imports.add(import_line)
                continue
        elif stmt is not None:
            definitions[stmt.lineno] = ast.unparse(stmt)
            pending.extend(_free_names(stmt))
            continue

        if name not in module_ns:
            continue
        import_line = _import_statement_for(name, module_ns[name], module.__name__)
        if import_line is None:
            raise UnsupportedFilterShape(
                filter_name=step_name,
                method_name=fn.name,
                line=getattr(fn, "lineno", 0),
                col=getattr(fn, "col_offset", 0),
                node_kind="Name",
                suggestion=(
                    f"`{name}` has no top-level definition or import in {module.__name__}'s source "
                    "and cannot be imported by name; define it at module level so export can copy it."
                ),
            )
        imports.add(import_line)

    return tuple(sorted(imports)), tuple(definitions[line] for line in sorted(definitions))


def _module_bindings(module) -> dict:
    """Map each name to the last top-level statement in the module that binds it."""
    try:
        tree = ast.parse(inspect.getsource(module))
    except (OSError, TypeError, SyntaxError):
        return {}
    bindings: dict = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                bindings[alias.asname or alias.name.split(".")[0]] = stmt
        elif isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                bindings[alias.asname or alias.name] = stmt
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings[stmt.name] = stmt
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                names: set = set()
                _collect_target_names(target, names)
                for name in names:
                    bindings[name] = stmt
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            if isinstance(stmt.target, ast.Name):
                bindings[stmt.target.id] = stmt
    return bindings


def _import_line_for_alias(stmt, name: str) -> Optional[str]:
    """Re-emit only the alias that binds ``name``; relative imports return None."""
    if isinstance(stmt, ast.ImportFrom):
        if stmt.level or stmt.module == "__future__":
            return None
        for alias in stmt.names:
            if (alias.asname or alias.name) == name:
                suffix = f" as {alias.asname}" if alias.asname else ""
                return f"from {stmt.module} import {alias.name}{suffix}"
        return None
    for alias in stmt.names:
        if (alias.asname or alias.name.split(".")[0]) == name:
            return f"import {alias.name} as {alias.asname}" if alias.asname else f"import {alias.name}"
    return None


def _free_names(stmt: ast.AST) -> set:
    """Names a copied top-level statement loads but does not itself bind."""
    loaded: set = set()
    bound: set = set()
    for node in ast.walk(stmt):
        if isinstance(node, ast.Name):
            (loaded if isinstance(node.ctx, ast.Load) else bound).add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
    return loaded - bound


def _local_names(fn: ast.FunctionDef) -> set:
    names = {"self", "cls"}
    args = fn.args
    for arg in list(args.args) + list(args.posonlyargs) + list(args.kwonlyargs):
        names.add(arg.arg)
    if args.vararg is not None:
        names.add(args.vararg.arg)
    if args.kwarg is not None:
        names.add(args.kwarg.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                _collect_target_names(target, names)
        elif isinstance(node, ast.AugAssign) or isinstance(node, ast.AnnAssign):
            _collect_target_names(node.target, names)
        elif isinstance(node, (ast.For, ast.comprehension)):
            _collect_target_names(node.target, names)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars is not None:
                    _collect_target_names(item.optional_vars, names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not fn:
            names.add(node.name)
    return names


def _collect_target_names(target: ast.AST, names: set) -> None:
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _collect_target_names(elt, names)
    elif isinstance(target, ast.Starred):
        _collect_target_names(target.value, names)


def _referenced_free_names(fn: ast.FunctionDef, local_names: set) -> Iterable[str]:
    seen: set = set()
    for node in ast.walk(fn):
        root = None
        if isinstance(node, ast.Name):
            root = node.id
        elif isinstance(node, ast.Attribute):
            root = _leftmost_name(node)
        if root and root not in local_names and root not in seen:
            seen.add(root)
            yield root


def _leftmost_name(node: ast.Attribute) -> Optional[str]:
    current = node.value
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


def _import_statement_for(local_name: str, value, current_module: str) -> Optional[str]:
    if isinstance(value, types.ModuleType):
        real_name = value.__name__
        if real_name == local_name:
            return f"import {real_name}"
        return f"import {real_name} as {local_name}"

    origin = getattr(value, "__module__", None)
    if not origin or origin == current_module or origin == "builtins":
        return None
    real_name = getattr(value, "__name__", local_name)
    # ``__module__`` names where a value's *type* lives, not where the value
    # can be imported from (a compiled pattern reports "re"). Only emit the
    # import if it would actually hand back this object.
    if getattr(sys.modules.get(origin), real_name, None) is not value:
        return None
    if real_name == local_name:
        return f"from {origin} import {local_name}"
    return f"from {origin} import {real_name} as {local_name}"
