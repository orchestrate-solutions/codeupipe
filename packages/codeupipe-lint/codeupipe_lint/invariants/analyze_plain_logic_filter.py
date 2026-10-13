"""AnalyzePlainLogicFilter: CUP-I008, a warning: logic that is not in a primitive.

A project that uses codeupipe writes its logic as Filters, Predicates, Taps,
Hooks and Pipelines. Logic in a plain function or a plain class works as
well, so nothing else shows the mistake. This rule shows it.

Logic is a decision or a loop: ``if``, ``a if c else b``, ``match``,
``for``, ``while``, ``try``. Flagged, once each: a function at the top of a
file, a class at the top of a file that is not a primitive, and the code at
the top of a file itself. Not flagged: a primitive (its logic is where it
must be), a function or a class with no logic, a test file, and the guards
``if __name__ == "__main__":`` and ``if TYPE_CHECKING:``. Not seen: a
comprehension, and ``and`` / ``or``.
"""

import ast

from codeupipe import Payload

from .primitive_kind import is_test_file, primitive_kind
from .rules import LOGIC_OUTSIDE_PRIMITIVE, make_finding

_WHAT = "has logic and is not a Filter, a Predicate, a Tap, a Hook or a Pipeline"
# ast.Match is new in Python 3.10 and ast.TryStar in 3.11.
_LOGIC = tuple(getattr(ast, name) for name in ("If", "IfExp", "For", "AsyncFor", "While", "Try", "TryStar", "Match")
               if hasattr(ast, name))
_GUARDS = ("__name__", "TYPE_CHECKING")


class AnalyzePlainLogicFilter:
    """Filter (sync).

    Input keys: ``trees`` ({path: ast.Module}), ``findings`` (list).
    Output keys: ``findings`` with CUP-I008 warnings appended.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path, tree in payload.get("trees", {}).items():
            if is_test_file(path):
                continue
            module_code = None
            for node in tree.body:
                what = None
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    what = "Function `%s`" % node.name if self.has_logic(node.body) else None
                elif isinstance(node, ast.ClassDef):
                    if primitive_kind(node) is None and self.has_logic(node.body):
                        what = "Class `%s`" % node.name
                elif module_code is None and self.has_logic(self.without_guard(node)):
                    module_code = node
                if what is not None:
                    findings.append(make_finding(path, node.lineno, node.col_offset + 1, LOGIC_OUTSIDE_PRIMITIVE,
                                                 "%s %s" % (what, _WHAT)))
            if module_code is not None:
                findings.append(make_finding(path, module_code.lineno, module_code.col_offset + 1,
                                             LOGIC_OUTSIDE_PRIMITIVE, "The code at the top of this file %s" % _WHAT))
        return payload.insert("findings", findings)

    def has_logic(self, nodes) -> bool:
        return any(isinstance(inner, _LOGIC) for node in nodes for inner in ast.walk(node))

    def without_guard(self, node):
        """The statements to look in: for a guard of the language, those in it, and not the ``if`` itself."""
        if isinstance(node, ast.If) and not node.orelse and any(
                isinstance(name, ast.Name) and name.id in _GUARDS or isinstance(name, ast.Attribute) and name.attr in _GUARDS
                for name in ast.walk(node.test)):
            return node.body
        return [node]
