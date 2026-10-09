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


def _membership(key: ast.expr, owner: str) -> ast.Compare:
    return ast.Compare(left=key, ops=[ast.In()], comparators=[ast.Name(id=owner, ctx=ast.Load())])


def _without(key: ast.expr) -> ast.DictComp:
    """``{k_: v_ for k_, v_ in data.items() if k_ != key}``: a new dict."""
    return ast.DictComp(
        key=ast.Name(id="_key", ctx=ast.Load()),
        value=ast.Name(id="_value", ctx=ast.Load()),
        generators=[ast.comprehension(
            target=ast.Tuple(elts=[ast.Name(id="_key", ctx=ast.Store()), ast.Name(id="_value", ctx=ast.Store())],
                             ctx=ast.Store()),
            iter=ast.Call(func=ast.Attribute(value=ast.Name(id="data", ctx=ast.Load()), attr="items",
                                             ctx=ast.Load()), args=[], keywords=[]),
            ifs=[ast.Compare(left=ast.Name(id="_key", ctx=ast.Load()), ops=[ast.NotEq()], comparators=[key])],
            is_async=0)])


def _is_lowered_payload(node: ast.AST) -> bool:
    """A dict expression this rewriter produced from a payload operation."""
    if isinstance(node, (ast.Dict, ast.DictComp)):
        return True
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict"
            and len(node.args) == 1 and not node.keywords)


_FRAMEWORK_MODULES = ("codeupipe", "codeupipe")


def _drop_unused_framework_imports(imports: tuple, *trees: ast.AST) -> tuple:
    """Lowering removes ``Payload``/``MutablePayload`` uses; drop their imports
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
_LOWERED_MEMBERS = frozenset({
    "get", "insert", "remove", "merge", "has", "to_dict", "with_mutation", "set",
})

_OBSERVABILITY_MEMBERS = frozenset({"trace_id", "lineage", "with_trace"})


class _PayloadToDictTransformer(ast.NodeTransformer):
    def __init__(self, filter_name: str, method_name: str, fn_name: str = ""):
        self.filter_name = filter_name  # the step's identity: for messages
        self.method_name = method_name
        self.fn_name = fn_name or filter_name  # the generated function's name
        # locals bound to ``payload.with_mutation()``: plain dicts once lowered
        self.mutables: set = set()

    def visit_Name(self, node: ast.Name):
        if node.id in {"State", "MutablePayload"}:
            raise self._error(node, "Name", "Stay within plain Payload + dict semantics for export.")
        if node.id == "payload":
            return ast.copy_location(ast.Name(id="data", ctx=node.ctx), node)
        return node

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "payload" and node.attr not in _LOWERED_MEMBERS:
            if node.attr in _OBSERVABILITY_MEMBERS:
                raise self._error(node, "Attribute",
                                  f"payload.{node.attr} has no static form: exported steps work on a "
                                  "plain dict, which carries no trace ID or lineage.")
            raise self._error(node, "Attribute",
                              f"payload.{node.attr} is not an exportable Payload operation "
                              f"({', '.join(sorted(_LOWERED_MEMBERS - {'set'}))}).")
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        raise self._error(node, "AsyncFunctionDef", "Static run() is sync; make the step sync to export it.")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for stmt in ast.walk(node):
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Attribute)
                    and stmt.value.func.attr == "with_mutation"):
                self.mutables.add(stmt.targets[0].id)
        node = self.generic_visit(node)
        node.name = self.fn_name
        node.args.args = [ast.arg(arg="data")]
        node.args.posonlyargs = []
        node.args.kwonlyargs = []
        node.args.kw_defaults = []
        node.args.defaults = []
        return node

    def visit_Expr(self, node: ast.Expr):
        """MutablePayload writes are statements: ``m.set(k, v)`` -> ``m[k] = v``."""
        call = node.value
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name) and call.func.value.id in self.mutables
                and call.func.attr in {"set", "remove"} and not call.keywords):
            target = call.func.value.id
            args = [self.visit(a) for a in call.args]
            if call.func.attr == "set" and len(args) == 2:
                return ast.copy_location(ast.Assign(
                    targets=[ast.Subscript(value=ast.Name(id=target, ctx=ast.Load()), slice=args[0], ctx=ast.Store())],
                    value=args[1]), node)
            if call.func.attr == "remove" and len(args) == 1:
                return ast.copy_location(ast.Expr(value=ast.Call(
                    func=ast.Attribute(value=ast.Name(id=target, ctx=ast.Load()), attr="pop", ctx=ast.Load()),
                    args=[args[0], ast.Constant(value=None)], keywords=[])), node)
        return self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        node = self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == "payload":
            node.value = ast.copy_location(ast.Name(id="data", ctx=ast.Load()), node.value)
        return node

    def visit_Call(self, node: ast.Call):
        if self._is_insert_chain(node):
            return ast.copy_location(self._collapse_insert_chain(node), node)

        node = self.generic_visit(node)

        # ``Payload(x)`` -> ``dict(x)``: a Payload is a dict once lowered.
        if isinstance(node.func, ast.Name) and node.func.id == "Payload" and not node.keywords:
            return ast.copy_location(ast.Call(func=ast.Name(id="dict", ctx=ast.Load()),
                                              args=node.args[:1], keywords=[]), node)

        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            owner = node.func.value

            if isinstance(owner, ast.Name) and owner.id in self.mutables:
                if attr in {"get"}:
                    return node
                if attr == "has" and len(node.args) == 1:
                    return ast.copy_location(_membership(node.args[0], owner.id), node)
                if attr == "to_immutable" and not node.args:
                    return ast.copy_location(_dict_of(ast.Name(id=owner.id, ctx=ast.Load())), node)
                raise self._error(node, "Attribute",
                                  "MutablePayload.set/remove are exportable only as statements.")

            # A payload operation applied to an already-lowered payload value
            # (``payload.remove(k).insert(...)``): the owner is now a plain
            # dict expression, so lower the operation on it too. Only our own
            # dict shapes qualify, never an arbitrary object's ``insert``.
            if _is_lowered_payload(owner) and not node.keywords:
                if attr == "insert" and len(node.args) == 2:
                    return ast.copy_location(ast.Dict(keys=[None, node.args[0]],
                                                      values=[owner, node.args[1]]), node)
                if attr == "merge" and len(node.args) == 1:
                    return ast.copy_location(ast.Dict(keys=[None, None], values=[owner, node.args[0]]), node)
                if attr == "has" and len(node.args) == 1:
                    return ast.copy_location(ast.Compare(left=node.args[0], ops=[ast.In()],
                                                         comparators=[owner]), node)
                if attr == "get":
                    return node

            if isinstance(owner, ast.Name) and owner.id == "data":
                if attr == "get":
                    return node
                if attr == "to_dict":
                    return ast.copy_location(
                        ast.Call(
                            func=ast.Name(id="dict", ctx=ast.Load()),
                            args=[ast.Name(id="data", ctx=ast.Load())],
                            keywords=[],
                        ),
                        node,
                    )
                if attr == "has" and len(node.args) == 1 and not node.keywords:
                    return ast.copy_location(_membership(node.args[0], "data"), node)
                if attr == "with_mutation" and not node.args:
                    return ast.copy_location(_dict_of(ast.Name(id="data", ctx=ast.Load())), node)
                if attr == "merge" and len(node.args) == 1 and not node.keywords:
                    # right side wins, as Payload.merge does
                    return ast.copy_location(ast.Dict(
                        keys=[None, None],
                        values=[ast.Name(id="data", ctx=ast.Load()), node.args[0]]), node)
                if attr == "remove" and len(node.args) == 1 and not node.keywords:
                    key = node.args[0]
                    if not isinstance(key, (ast.Constant, ast.Name)):
                        raise self._error(node, "Call",
                                          "payload.remove needs a literal or a name as its key to export.")
                    return ast.copy_location(_without(key), node)
                if attr == "set":
                    raise self._error(node, "Attribute", "Rewrite payload.set to an assignment statement before export.")
                if attr != "insert":
                    raise self._error(node, "Attribute", "Exportable Payload operations: get, insert, remove, merge, has, to_dict, with_mutation.")

        return node

    def _collapse_insert_chain(self, node: ast.Call):
        pairs = []
        current = node
        while True:
            if not isinstance(current, ast.Call):
                raise self._error(node, "Call", "Insert chain must terminate at payload.")
            if not isinstance(current.func, ast.Attribute) or current.func.attr != "insert":
                raise self._error(node, "Attribute", "Only chained payload.insert calls are supported.")
            if len(current.args) != 2:
                raise self._error(current, "Call", "payload.insert must take exactly two positional arguments.")
            # Any key expression: plain Python evaluates a computed key exactly
            # as Payload.insert does (configurable filters insert `self.key`).
            key = self.visit(current.args[0])
            value = self.visit(current.args[1])
            pairs.append((key, value))
            base = current.func.value
            if isinstance(base, ast.Name) and base.id == "payload":
                break
            current = base

        pairs.reverse()
        merged = ast.Dict(
            keys=[None] + [key for key, _value in pairs],
            values=[ast.Name(id="data", ctx=ast.Load())] + [value for _key, value in pairs],
        )
        return merged

    def _is_insert_chain(self, node: ast.Call) -> bool:
        current = node
        seen_insert = False
        while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
            if current.func.attr != "insert":
                return False
            seen_insert = True
            base = current.func.value
            if isinstance(base, ast.Name) and base.id == "payload":
                return seen_insert
            current = base
        return False

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
