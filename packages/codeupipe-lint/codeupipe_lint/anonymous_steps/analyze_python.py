"""AnalyzePython: anonymous steps in Python files, via the stdlib ``ast``.

See PythonStepVisitor for what is flagged.
"""

import ast

from codeupipe import Payload

from .python_step_visitor import PythonStepVisitor
from .rules import PARSE_ERROR, make_finding


class AnalyzePython:
    """Filter (sync).

    Input keys: ``files`` ({lang: [path]}), ``findings`` (list).
    Output keys: ``findings`` with Python findings appended.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path in payload.get("files", {}).get("python", []):
            with open(path, encoding="utf-8", errors="replace") as handle:
                source = handle.read()
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError as error:
                findings.append(make_finding("python", path, error.lineno or 1, error.offset or 1, PARSE_ERROR,
                                             "File", "is not valid Python (%s)" % error.msg))
                continue
            findings.extend(PythonStepVisitor(path, tree).findings())
        return payload.insert("findings", findings)
