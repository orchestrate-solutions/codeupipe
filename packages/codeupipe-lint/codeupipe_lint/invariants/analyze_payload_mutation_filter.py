"""AnalyzePayloadMutationFilter: CUP-I001 and CUP-I002 in Python step methods.

See PayloadMutationVisitor for what is flagged.
"""

import ast

from codeupipe import Payload

from .payload_mutation_visitor import STEP_METHODS, PayloadMutationVisitor


class AnalyzePayloadMutationFilter:
    """Filter (sync).

    Input keys: ``trees`` ({path: ast.Module}), ``findings`` (list).
    Output keys: ``findings`` with payload-mutation findings appended.
    Checked: methods named ``call``, ``observe`` or ``test`` of any class.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path, tree in payload.get("trees", {}).items():
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for member in node.body:
                    if (isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and member.name in STEP_METHODS):
                        findings.extend(PayloadMutationVisitor(path, member).found)
        return payload.insert("findings", findings)
