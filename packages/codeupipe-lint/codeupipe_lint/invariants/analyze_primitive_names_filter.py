"""AnalyzePrimitiveNamesFilter: CUP-I006 and CUP-I007, the names of primitives.

CUP-I007: the class name of a primitive ends with its role, so a name tells
what the class is: ``DiscountFilter``, ``AuditTap``, ``PrintStepsHook``,
``AtLeastPredicate``, ``PricingPipeline``.

CUP-I006: the file name is the class name in snake_case, the standard for a
Python module: ``DiscountFilter`` is in ``discount_filter.py``. The file name
that the rule asks for already includes the role.

Checked: primitive classes at module level. Not checked: plain classes, and
test files.
"""

import ast
import os
import re

from codeupipe import Payload

from .primitive_kind import is_test_file, primitive_kind
from .rules import PRIMITIVE_FILE_NAME, PRIMITIVE_ROLE_SUFFIX, make_finding

__all__ = ["AnalyzePrimitiveNamesFilter", "snake_case"]

# kind (primitive_kind) -> the endings a class name of that kind may have
_ROLE_SUFFIXES = {
    "Filter": ("Filter", "Valve"),  # the library's own Valve class has the shape of a Filter
    "Tap": ("Tap",),
    "Hook": ("Hook",),
    "predicate": ("Predicate",),
    "Pipeline": ("Pipeline",),
}

_WORD_BREAK = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def snake_case(class_name: str) -> str:
    """``ParseHTMLFilter`` -> ``parse_html_filter``."""
    return _WORD_BREAK.sub("_", class_name).lower()


class AnalyzePrimitiveNamesFilter:
    """Filter (sync).

    Input keys: ``trees`` ({path: ast.Module}), ``findings`` (list).
    Output keys: ``findings`` with CUP-I006 and CUP-I007 findings appended.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path, tree in payload.get("trees", {}).items():
            if is_test_file(path):
                continue
            stem = os.path.splitext(os.path.basename(path))[0]
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                kind = primitive_kind(node)
                if kind is None:
                    continue
                suffixes = _ROLE_SUFFIXES[kind]
                wanted = node.name
                if not node.name.endswith(suffixes):
                    wanted = node.name + suffixes[0]
                    findings.append(make_finding(
                        path, node.lineno, node.col_offset + 1, PRIMITIVE_ROLE_SUFFIX,
                        "%s `%s` does not say what it is. Name it `%s`" % (kind, node.name, wanted)))
                if stem != snake_case(wanted):
                    findings.append(make_finding(
                        path, node.lineno, node.col_offset + 1, PRIMITIVE_FILE_NAME,
                        "`%s` is in `%s.py`. Put it in `%s.py`" % (wanted, stem, snake_case(wanted))))
        return payload.insert("findings", findings)
