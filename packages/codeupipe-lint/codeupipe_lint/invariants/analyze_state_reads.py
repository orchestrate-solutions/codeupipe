"""AnalyzeStateReads: CUP-I003 in Python Filters and Valve predicates.

See StateReadVisitor for what is flagged.
"""

import ast

from codeupipe import Payload

from .state_read_visitor import STEP_METHODS, StateReadVisitor, state_handles


class AnalyzeStateReads:
    """Filter (sync).

    Input keys: ``trees`` ({path: ast.Module}), ``findings`` (list).
    Output keys: ``findings`` with state-read findings appended.
    Checked: methods named ``call`` or ``test`` of any class.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path, tree in payload.get("trees", {}).items():
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                handles = state_handles(node)
                for member in node.body:
                    if (isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and member.name in STEP_METHODS):
                        findings.extend(StateReadVisitor(path, member, handles).found)
        return payload.insert("findings", findings)
