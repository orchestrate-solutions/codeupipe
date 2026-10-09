"""AnalyzePython: anonymous steps in Python files, via the stdlib ``ast``.

See PythonStepVisitor for what is flagged.

Scope: step identity is the contract of ``codeupipe.core``'s Pipeline. The
typed variant in NAMED_STEP_APIS (core/typed) takes hand-written step names
and does not derive identity, so a module that imports from it and not from
the identity core is skipped.
"""

import ast

from codeupipe import Payload

from .python_step_visitor import PythonStepVisitor
from .rules import PARSE_ERROR, make_finding

NAMED_STEP_APIS = ("codeupipe.core.typed",)
IDENTITY_APIS = ("codeupipe", "codeupipe.core", "codeupipe.core.pipeline", "codeupipe.core.valve")


def uses_only_named_step_api(tree: ast.Module) -> bool:
    """True when the module imports a named-step variant and not the identity core."""
    named = identity = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            if any(node.module == m or node.module.startswith(m + ".") for m in NAMED_STEP_APIS):
                named = True
            elif node.module in IDENTITY_APIS:
                identity = True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in IDENTITY_APIS:
                    identity = True
    return named and not identity


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
            if uses_only_named_step_api(tree):
                continue
            findings.extend(PythonStepVisitor(path, tree).findings())
        return payload.insert("findings", findings)
