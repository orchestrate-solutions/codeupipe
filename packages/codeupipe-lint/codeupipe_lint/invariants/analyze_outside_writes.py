"""AnalyzeOutsideWrites: CUP-I004 in Python Taps, Hooks and Valve predicates.

See OutsideWriteVisitor for what is flagged.
"""

import ast

from codeupipe import Payload

from .outside_write_visitor import READER_METHODS, OutsideWriteVisitor


class AnalyzeOutsideWrites:
    """Filter (sync).

    Input keys: ``trees`` ({path: ast.Module}), ``findings`` (list).
    Output keys: ``findings`` with outside-write findings appended.
    Checked: methods named ``observe``, ``test``, ``before``, ``after`` or
    ``on_error`` of any class.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path, tree in payload.get("trees", {}).items():
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for member in node.body:
                    if (isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and member.name in READER_METHODS):
                        findings.extend(OutsideWriteVisitor(path, member).found)
        return payload.insert("findings", findings)
