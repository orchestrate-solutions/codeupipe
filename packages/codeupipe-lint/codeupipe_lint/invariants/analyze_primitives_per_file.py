"""AnalyzePrimitivesPerFile: CUP-I005, one primitive in each file.

A Filter, a Tap, a Hook, a predicate or a named Pipeline alone in its file
can be found by its name, tested alone, and used again in another pipeline.
The pipeline file is where they come together.

Flagged: every primitive class at module level after the first. Not
flagged: plain classes and functions beside the primitive, classes inside a
function, and test files (a test often needs several small steps side by
side).
"""

import ast

from codeupipe import Payload

from .primitive_kind import is_test_file, primitive_kind
from .rules import ONE_PRIMITIVE_PER_FILE, make_finding


class AnalyzePrimitivesPerFile:
    """Filter (sync).

    Input keys: ``trees`` ({path: ast.Module}), ``findings`` (list).
    Output keys: ``findings`` with CUP-I005 findings appended.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path, tree in payload.get("trees", {}).items():
            if is_test_file(path):
                continue
            first = None
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                kind = primitive_kind(node)
                if kind is None:
                    continue
                if first is None:
                    first = (node.name, kind)
                    continue
                findings.append(make_finding(
                    path, node.lineno, node.col_offset + 1, ONE_PRIMITIVE_PER_FILE,
                    "%s `%s` shares this file with %s `%s`" % (kind, node.name, first[1], first[0])))
        return payload.insert("findings", findings)
