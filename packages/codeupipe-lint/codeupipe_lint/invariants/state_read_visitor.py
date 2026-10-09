"""StateReadVisitor: pipeline State reached from a Filter or a Valve predicate.

A step is never handed State, so it can only read it through something it
holds. Inside ``call`` and ``test`` this flags:

* ``<x>.state.<member>`` where the member is one of State's own
  (``executed``, ``skipped``, ``errors``, ``timings``, ``has_errors()``, ...);
* ``<pipeline>.state`` in any form, when the name it hangs off says it is a
  pipeline (``self.pipeline.state``, ``PIPELINE.state.get("flag")``);
* any use of an attribute the class's ``__init__`` set to a State: from a
  parameter annotated ``State``, from ``<x>.state``, or from ``State()``.

Not flagged: ``self.state`` when it is the step's own attribute, a Payload
key or nested value called "state", and anything in ``observe`` or a Hook
method, since Taps and Hooks are observers.
"""

import ast

from .rules import STATE_READ, make_finding

STEP_METHODS = {"call", "test"}
STATE_MEMBERS = {"executed", "skipped", "errors", "timings", "metadata", "chunks_processed", "mark_executed",
                 "mark_skipped", "increment_chunks", "record_timing", "record_error", "has_errors",
                 "last_error", "reset", "diff"}


def _is_state_type(node) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "State"
    if isinstance(node, ast.Attribute):
        return node.attr == "State"
    return isinstance(node, ast.Constant) and node.value == "State"


def _is_self(node) -> bool:
    return isinstance(node, ast.Name) and node.id == "self"


def _names_a_pipeline(node) -> bool:
    name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else ""
    return "pipeline" in name.lower()


def state_handles(class_node) -> set:
    """Attributes that ``__init__`` sets to a State."""
    handles = set()
    for member in class_node.body:
        if not (isinstance(member, ast.FunctionDef) and member.name == "__init__"):
            continue
        state_parameters = {a.arg for a in member.args.args + member.args.kwonlyargs
                            if a.annotation is not None and _is_state_type(a.annotation)}
        for node in ast.walk(member):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            is_state = ((isinstance(value, ast.Name) and value.id in state_parameters)
                        or (isinstance(value, ast.Attribute) and value.attr == "state")
                        or (isinstance(value, ast.Call) and _is_state_type(value.func)))
            if is_state:
                handles.update(t.attr for t in node.targets if isinstance(t, ast.Attribute) and _is_self(t.value))
    return handles


class StateReadVisitor(ast.NodeVisitor):
    def __init__(self, path, method, handles):
        self.path = path
        self.handles = handles
        self.found = []
        for statement in method.body:
            self.visit(statement)

    def _reaches_state(self, node) -> bool:
        outer = None
        while isinstance(node, ast.Attribute):
            if _is_self(node.value) and node.attr in self.handles:
                return True
            if node.attr == "state" and not _is_self(node.value):
                if outer in STATE_MEMBERS or _names_a_pipeline(node.value):
                    return True
            outer = node.attr
            node = node.value
        return False

    def visit_Attribute(self, node):
        if self._reaches_state(node):
            self.found.append(make_finding(self.path, node.lineno, node.col_offset + 1, STATE_READ,
                                           "Step reads pipeline State (`%s`)" % ast.unparse(node)))
            return
        self.generic_visit(node)

    def _skip(self, node):
        """A nested function or class is its own scope."""

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_Lambda = _skip
