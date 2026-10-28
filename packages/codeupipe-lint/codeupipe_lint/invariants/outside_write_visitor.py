"""OutsideWriteVisitor: a write to the Payload from a method that only reads it.

Only a Filter writes to the Payload. A Tap (``observe``), a Valve predicate
(``test``) and a Hook (``before``, ``after``, ``on_error``) read it. The
runtime does not check, so this rule is the guard. This
walks one such method and flags a call of ``insert``, ``remove``, ``merge``
or ``with_trace`` on the method's payload parameter, a chain of them included.

Not flagged: a write to a copy (``payload.copy().insert(..)``, or a name
bound to ``payload.copy()``), and the same method names on any other object
(``self.rows.insert(0, ..)``).
"""

import ast

from .rules import WRITE_OUTSIDE_FILTER, make_finding

READER_METHODS = {"observe", "test", "before", "after", "on_error"}
WRITES = {"insert", "remove", "merge", "with_trace"}


# cup: allow-plain used by the analysis Filters and the visitor: it finds the payload parameter of a method
def payload_parameter(method):
    """The parameter that holds the Payload: the one named ``payload``, else the last one."""
    names = [a.arg for a in method.args.posonlyargs + method.args.args]
    if names and names[0] in ("self", "cls"):
        names = names[1:]
    if not names:
        return None
    return "payload" if "payload" in names else names[-1]


# cup: allow-plain a visitor of a syntax tree: the tool that a Filter uses to read or change source code
class OutsideWriteVisitor(ast.NodeVisitor):
    def __init__(self, path, method):
        self.path = path
        self.method = method.name
        self.payload = payload_parameter(method)
        self.found = []
        if self.payload is not None:
            for statement in method.body:
                self.visit(statement)

    def _writes_the_payload(self, call) -> bool:
        """True for ``<payload>.<write>(..)``, and for a write chained onto one."""
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr in WRITES):
            return False
        owner = call.func.value
        if isinstance(owner, ast.Name):
            return owner.id == self.payload
        return self._writes_the_payload(owner)

    def visit_Call(self, node):
        if self._writes_the_payload(node):
            self.found.append(make_finding(
                self.path, node.lineno, node.col_offset + 1, WRITE_OUTSIDE_FILTER,
                "`%s` writes to the Payload (`%s.%s`)" % (self.method, self.payload, node.func.attr)))
            for argument in node.args:  # the chain is one finding; its arguments are still checked
                self.visit(argument)
            return
        self.generic_visit(node)

    def _skip(self, node):
        """A nested function or class is its own scope."""

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_Lambda = _skip
