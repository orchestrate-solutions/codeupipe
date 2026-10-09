"""ParsePython: parse each Python file once, for every analyzer after it."""

import ast

from codeupipe import Payload

from .rules import PARSE_ERROR, make_finding


class ParsePython:
    """Filter (sync).

    Input keys: ``files`` ({lang: [path]}), ``findings`` (list).
    Output keys: ``trees`` ({path: ast.Module}) and ``findings`` with one
    CUP-I000 per file that could not be parsed. An unparsable file is
    reported, never skipped as clean.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        trees = {}
        for path in payload.get("files", {}).get("python", []):
            with open(path, encoding="utf-8", errors="replace") as handle:
                source = handle.read()
            try:
                trees[path] = ast.parse(source, filename=path)
            except SyntaxError as error:
                findings.append(make_finding(path, error.lineno or 1, error.offset or 1, PARSE_ERROR,
                                             "File is not valid Python (%s)" % error.msg))
        return payload.insert("trees", trees).insert("findings", findings)
