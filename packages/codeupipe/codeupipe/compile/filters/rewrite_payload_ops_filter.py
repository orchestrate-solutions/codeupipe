"""
RewritePayloadOpsFilter — CUP payload API -> plain dict operations.

Direction: export (CUP -> standard Python).
Milestone: M0.

This filter is the workhorse of the export path. It walks each Filter's
``call`` AST and replaces payload-shaped calls with dict-shaped ones.
"""

from __future__ import annotations

import ast
from dataclasses import replace

from codeupipe.core import Payload

from ..errors import UnsupportedFilterShape


__all__ = ["RewritePayloadOpsFilter"]


def _dict_of(value: ast.expr) -> ast.Call:
    return ast.Call(func=ast.Name(id="dict", ctx=ast.Load()), args=[value], keywords=[])


def _membership(key: ast.expr, owner: ast.expr) -> ast.Compare:
    return ast.Compare(left=key, ops=[ast.In()], comparators=[owner])


def _name(identifier: str, ctx=None) -> ast.Name:
    return ast.Name(id=identifier, ctx=ctx or ast.Load())


_FRAMEWORK_MODULES = ("codeupipe", "codeupipe")


def _drop_unused_framework_imports(imports: tuple, *trees: ast.AST) -> tuple:
    """Lowering removes ``Payload`` uses; drop their imports
    so no framework import survives into the emitted package."""
    used = {n.id for tree in trees if tree is not None for n in ast.walk(tree) if isinstance(n, ast.Name)}
    kept = []
    for line in imports:
        stmt = ast.parse(line).body[0]
        module = getattr(stmt, "module", None) or (stmt.names[0].name if isinstance(stmt, ast.Import) else "")
        bound = {a.asname or a.name.split(".")[0] for a in stmt.names}
        if module.split(".")[0] in _FRAMEWORK_MODULES and not (bound & used):
            continue
        kept.append(line)
    return tuple(kept)


# Payload members this rewriter lowers. Anything else read off the payload
# (``trace_id``, ``lineage``, ``with_trace``, ``_data``) has no plain-dict
# counterpart and would otherwise pass through as ``data.<attr>`` on a dict,
# failing only when the exported code runs.
_READS = frozenset({"get", "has", "to_dict", "copy"})
_WRITES = frozenset({"insert", "remove", "merge"})
_LOWERED_MEMBERS = _READS | _WRITES

_OBSERVABILITY_MEMBERS = frozenset({"trace_id", "lineage", "with_trace"})

_WRITE_ARITY = {"insert": 2, "remove": 1, "merge": 1}

_WRITE_SITE = ("A Payload write (insert, remove, merge) exports as a statement of its own, as the value "
               "of a return, or as the value assigned to a name. Move it out of the larger expression.")


class _PayloadToDictTransformer(ast.NodeTransformer):
    """Lower a step's Payload operations to operations on a plain dict.

    A Payload write changes the Payload in place and returns it, so the plain
    form of a write is a statement on the dict: ``payload.insert(k, v)`` is
    ``data[k] = v``. A name bound to a Payload (``payload`` itself, an alias,
    or a ``copy()``) becomes a name bound to a dict.
    """

    def __init__(self, filter_name: str, method_name: str, fn_name: str = ""):
        self.filter_name = filter_name  # the step's label: for messages
        self.method_name = method_name
        self.fn_name = fn_name or filter_name  # the generated function's name
        # source name bound to a Payload -> the dict variable it becomes
        self.payloads = {"payload": "data"}
        self._temps = 0

    # -- which expressions are Payloads ---------------------------------

    def _is_payload(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self.payloads
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "Payload":
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr in _WRITES | {"copy"}:
                return self._is_payload(node.func.value)
        return False

    def _has_write(self, node: ast.AST) -> bool:
        while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _WRITES and self._is_payload(node.func.value):
                return True
            node = node.func.value
        return False

    def _lower_payload(self, node: ast.AST, statements: list) -> ast.expr:
        """The dict expression for a Payload expression; its writes, in
        evaluation order, are appended to ``statements``."""
        if isinstance(node, ast.Name):
            return _name(self.payloads[node.id])
        call = node
        if isinstance(call.func, ast.Name):  # Payload(x)
            if call.keywords or len(call.args) > 1:
                raise self._error(call, "Call", "Payload(...) exports with one positional argument, or none.")
            return _dict_of(self.visit(call.args[0])) if call.args else ast.Dict(keys=[], values=[])
        attr = call.func.attr
        owner = self._lower_payload(call.func.value, statements)
        if attr == "copy":
            if call.args or call.keywords:
                raise self._error(call, "Call", "payload.copy() takes no arguments.")
            return _dict_of(owner)
        if self.method_name in ("observe", "test"):
            raise self._error(call, "Call",
                              "A Tap or a predicate that writes to the Payload has no static form: "
                              "it observes, it does not change.")
        if call.keywords or len(call.args) != _WRITE_ARITY[attr]:
            raise self._error(call, "Call", f"payload.{attr} takes {_WRITE_ARITY[attr]} positional argument(s).")
        if not isinstance(owner, ast.Name):  # a fresh dict (a copy): it needs a name to be written to
            self._temps += 1
            temp = f"_copy_{self._temps}"
            statements.append(ast.Assign(targets=[_name(temp, ast.Store())], value=owner))
            owner = _name(temp)
        target = owner.id
        if attr == "insert":
            key, value = self.visit(call.args[0]), self.visit(call.args[1])
            statements.append(ast.Assign(
                targets=[ast.Subscript(value=_name(target), slice=key, ctx=ast.Store())], value=value))
        elif attr == "remove":
            statements.append(ast.Expr(value=ast.Call(
                func=ast.Attribute(value=_name(target), attr="pop", ctx=ast.Load()),
                args=[self.visit(call.args[0]), ast.Constant(value=None)], keywords=[])))
        else:  # merge: the other side wins
            statements.append(ast.Expr(value=ast.Call(
                func=ast.Attribute(value=_name(target), attr="update", ctx=ast.Load()),
                args=[self._lower_other(call.args[0])], keywords=[])))
        return _name(target)

    def _lower_other(self, node: ast.AST) -> ast.expr:
        """The argument of ``merge``: a Payload expression with no writes of its own."""
        if self._is_payload(node):
            if self._has_write(node):
                raise self._error(node, "Call", _WRITE_SITE)
            return self._lower_payload(node, [])
        return self.visit(node)

    def _located(self, statements: list, like: ast.AST) -> list:
        return [ast.copy_location(stmt, like) for stmt in statements]

    # -- statements: where a write may stand ----------------------------

    def visit_Expr(self, node: ast.Expr):
        if self._is_payload(node.value) and self._has_write(node.value):
            statements: list = []
            self._lower_payload(node.value, statements)
            return self._located(statements, node)
        return self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        if node.value is not None and self._is_payload(node.value):
            statements: list = []
            value = self._lower_payload(node.value, statements)
            return self._located(statements + [ast.Return(value=value)], node)
        return self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and self._is_payload(node.value)):
            source = node.targets[0].id
            statements: list = []
            value = self._lower_payload(node.value, statements)
            variable = self.payloads.setdefault(source, "data" if source == "payload" else source)
            if not (isinstance(value, ast.Name) and value.id == variable):
                statements.append(ast.Assign(targets=[_name(variable, ast.Store())], value=value))
            return self._located(statements or [ast.Pass()], node)
        return self.generic_visit(node)

    # -- expressions ----------------------------------------------------

    def visit_Name(self, node: ast.Name):
        if node.id == "State":
            raise self._error(node, "Name", "Stay within plain Payload + dict semantics for export.")
        if node.id in self.payloads:
            return ast.copy_location(ast.Name(id=self.payloads[node.id], ctx=node.ctx), node)
        return node

    def visit_Attribute(self, node: ast.Attribute):
        if (isinstance(node.value, ast.Name) and node.value.id in self.payloads
                and node.attr not in _LOWERED_MEMBERS):
            if node.attr in _OBSERVABILITY_MEMBERS:
                raise self._error(node, "Attribute",
                                  f"payload.{node.attr} has no static form: exported steps work on a "
                                  "plain dict, which carries no trace ID or lineage.")
            raise self._error(node, "Attribute",
                              f"payload.{node.attr} is not an exportable Payload operation "
                              f"({', '.join(sorted(_LOWERED_MEMBERS))}).")
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        raise self._error(node, "AsyncFunctionDef", "Static run() is sync; make the step sync to export it.")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node = self.generic_visit(node)
        node.name = self.fn_name
        node.args.args = [ast.arg(arg="data")]
        node.args.posonlyargs = []
        node.args.kwonlyargs = []
        node.args.kw_defaults = []
        node.args.defaults = []
        return node

    def visit_Call(self, node: ast.Call):
        if self._is_payload(node):
            if self._has_write(node):
                raise self._error(node, "Call", _WRITE_SITE)
            return ast.copy_location(self._lower_payload(node, []), node)  # copy(), Payload(x)

        if isinstance(node.func, ast.Attribute) and self._is_payload(node.func.value):
            attr = node.func.attr
            if attr in ("get", "has", "to_dict"):
                if self._has_write(node.func.value):
                    raise self._error(node, "Call", _WRITE_SITE)
                owner = self._lower_payload(node.func.value, [])
                args = [self.visit(arg) for arg in node.args]
                keywords = [ast.keyword(arg=kw.arg, value=self.visit(kw.value)) for kw in node.keywords]
                if attr == "get":
                    return ast.copy_location(ast.Call(
                        func=ast.Attribute(value=owner, attr="get", ctx=ast.Load()),
                        args=args, keywords=keywords), node)
                if attr == "has" and len(args) == 1 and not keywords:
                    return ast.copy_location(_membership(args[0], owner), node)
                if attr == "to_dict" and not args and not keywords:
                    return ast.copy_location(_dict_of(owner), node)
                raise self._error(node, "Call", f"payload.{attr} was called with arguments it does not take.")

        return self.generic_visit(node)

    def _error(self, node: ast.AST, node_kind: str, suggestion: str) -> UnsupportedFilterShape:
        return UnsupportedFilterShape(
            filter_name=self.filter_name,
            method_name=self.method_name,
            line=getattr(node, "lineno", 0),
            col=getattr(node, "col_offset", 0),
            node_kind=node_kind,
            suggestion=suggestion,
        )


class RewritePayloadOpsFilter:
    """Lower ``payload.*`` calls to plain ``data`` operations.

    Payload contract:
        Input:
            ``pipeline_ir`` (PipelineIR) — steps whose ``call_ast`` still
            speaks the CUP payload API.
        Output:
            ``pipeline_ir`` replaced with a new PipelineIR whose ``call_ast``
            (and ``predicate_ast`` for valves) uses only dict operations.
    """

    def call(self, payload: Payload) -> Payload:
        pipeline_ir = payload.get("pipeline_ir")
        rewritten_steps = []

        for step in pipeline_ir.steps:
            call_transformer = _PayloadToDictTransformer(step.name, step.call_ast.name, step.ident)
            call_ast = ast.fix_missing_locations(call_transformer.visit(ast.parse(ast.unparse(step.call_ast)).body[0]))
            predicate_ast = step.predicate_ast
            if predicate_ast is not None:
                predicate_name = getattr(predicate_ast, "name", "predicate")
                predicate_transformer = _PayloadToDictTransformer(step.name, predicate_name, step.ident)
                predicate_ast = ast.fix_missing_locations(
                    predicate_transformer.visit(ast.parse(ast.unparse(predicate_ast)).body[0])
                )
            imports = _drop_unused_framework_imports(tuple(step.imports or ()), call_ast, predicate_ast)
            rewritten_steps.append(replace(step, call_ast=call_ast, predicate_ast=predicate_ast, imports=imports))

        return payload.insert("pipeline_ir", replace(pipeline_ir, steps=rewritten_steps))
