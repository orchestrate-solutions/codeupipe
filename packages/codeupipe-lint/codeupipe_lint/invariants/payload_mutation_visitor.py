"""PayloadMutationVisitor: in-place changes to a Payload, inside one step method.

A Payload is immutable only at the top level: ``payload.get("items")`` hands
back the live list, shared with every earlier Payload and with the caller's
input. This walks a step method (``call``, ``observe``, ``test``) in source
order and flags:

* CUP-I001: a write through ``<payload>._data``;
* CUP-I002: an in-place change to a value that came from ``<payload>.get(..)``,
  directly or through a local name, including the loop variable of a ``for``
  over one.

Not flagged: ``payload.with_mutation()`` (the sanctioned in-place path), a
copy (``list(x)``, ``dict(x)``, ``x[:]``, ``x.copy()``, ``sorted(x)``), a name
rebound before it is changed, and ``name += ..`` on a local name, which is
almost always a number or a string.
"""

import ast

from .rules import PAYLOAD_INTERNALS, SHARED_VALUE_MUTATION, make_finding

STEP_METHODS = {"call", "observe", "test"}
PAYLOAD_RETURNING = {"insert", "remove", "merge", "with_trace"}
MUTATORS = {"append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse", "update", "setdefault",
            "popitem", "add", "discard", "difference_update", "intersection_update",
            "symmetric_difference_update", "appendleft", "extendleft", "popleft"}


def _base(node):
    """The name or call an attribute/subscript chain hangs off."""
    while isinstance(node, (ast.Subscript, ast.Attribute)):
        node = node.value
    return node


class PayloadMutationVisitor(ast.NodeVisitor):
    def __init__(self, path, method):
        self.path = path
        self.found = []
        parameters = method.args.args
        self.payloads = {parameters[1].arg} if len(parameters) > 1 else set()
        self.shared = set()
        for statement in method.body:
            self.visit(statement)

    # -- what an expression is ------------------------------------------------

    def _is_payload(self, node) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self.payloads
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in PAYLOAD_RETURNING and self._is_payload(node.func.value))

    def _is_get(self, node) -> bool:
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and self._is_payload(node.func.value))

    def _yields_shared(self, node) -> bool:
        """True when the expression can evaluate to a value a Payload holds."""
        if self._is_get(node):
            return True
        if isinstance(node, ast.Name):
            return node.id in self.shared
        if isinstance(node, ast.BoolOp):
            return any(self._yields_shared(value) for value in node.values)
        if isinstance(node, ast.IfExp):
            return self._yields_shared(node.body) or self._yields_shared(node.orelse)
        return False

    def _is_internals(self, node) -> bool:
        return (isinstance(node, ast.Attribute) and node.attr == "_data" and self._is_payload(node.value))

    def _describe(self, base) -> str:
        if isinstance(base, ast.Name):
            return "`%s` came from a Payload's get() and is changed in place" % base.id
        return "The value returned by payload.get() is changed in place"

    # -- reporting ------------------------------------------------------------

    def _report(self, node, rule, what):
        self.found.append(make_finding(self.path, node.lineno, node.col_offset + 1, rule, what))

    def _check_write_target(self, target, statement):
        if not isinstance(target, (ast.Subscript, ast.Attribute)):
            return
        chain = target.value
        while isinstance(chain, (ast.Subscript, ast.Attribute)) and not self._is_internals(chain):
            chain = chain.value
        if self._is_internals(chain):
            self._report(statement, PAYLOAD_INTERNALS, "Writes a Payload's internals (`_data`)")
            return
        base = _base(target)
        if isinstance(target, ast.Subscript) and (self._is_get(base) or
                                                  (isinstance(base, ast.Name) and base.id in self.shared)):
            self._report(statement, SHARED_VALUE_MUTATION, self._describe(base))

    def _bind(self, target, value):
        if not isinstance(target, ast.Name):
            return
        self.payloads.discard(target.id)
        self.shared.discard(target.id)
        if self._is_payload(value):
            self.payloads.add(target.id)
        elif self._yields_shared(value):
            self.shared.add(target.id)

    # -- statements -----------------------------------------------------------

    def visit_Assign(self, node):
        self.visit(node.value)
        for target in node.targets:
            self._check_write_target(target, node)
            self._bind(target, node.value)

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self.visit(node.value)
            self._check_write_target(node.target, node)
            self._bind(node.target, node.value)

    def visit_AugAssign(self, node):
        self.visit(node.value)
        self._check_write_target(node.target, node)

    def visit_Delete(self, node):
        for target in node.targets:
            self._check_write_target(target, node)

    def visit_For(self, node):
        self.visit(node.iter)
        if isinstance(node.target, ast.Name):
            self.payloads.discard(node.target.id)
            self.shared.discard(node.target.id)
            if self._yields_shared(node.iter):
                self.shared.add(node.target.id)
        for statement in node.body + node.orelse:
            self.visit(statement)

    visit_AsyncFor = visit_For

    def visit_Call(self, node):
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr in MUTATORS:
            receiver = function.value
            if self._is_internals(receiver):
                self._report(node, PAYLOAD_INTERNALS, "Writes a Payload's internals (`_data`)")
            else:
                base = _base(receiver)
                if self._is_get(base) or (isinstance(base, ast.Name) and base.id in self.shared):
                    self._report(node, SHARED_VALUE_MUTATION, self._describe(base))
        self.generic_visit(node)

    def _skip(self, node):
        """A nested function or class is its own scope; step methods are found from the module."""

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_Lambda = _skip
