"""ApplySuppressionsFilter: drop findings marked ``cup: allow-anonymous``.

The marker (``# cup: allow-anonymous`` / ``// cup: allow-anonymous``, any
trailing text) suppresses a finding when it is on the finding's line, on the
line of the enclosing add call, or alone on the line directly above.
"""

import re

from codeupipe import Payload

MARKER = re.compile(r"cup:\s*allow-anonymous\b")
_COMMENT_ONLY = re.compile(r"^\s*(#|//|/\*|\*)")


class ApplySuppressionsFilter:
    """Filter (sync).

    Input keys: ``findings``.
    Output keys: ``findings`` (kept), ``suppressed`` (dropped).
    ``marker`` is the comment that suppresses; other linters pass their own.
    """

    def __init__(self, marker=MARKER):
        self.marker = marker

    def call(self, payload: Payload) -> Payload:
        cache = {}
        kept, suppressed = [], []
        for finding in payload.get("findings", []):
            lines = cache.get(finding.path)
            if lines is None:
                try:
                    with open(finding.path, encoding="utf-8", errors="replace") as handle:
                        lines = handle.read().splitlines()
                except OSError:
                    lines = []
                cache[finding.path] = lines
            (suppressed if _is_suppressed(finding, lines, self.marker) else kept).append(finding)
        return payload.insert("findings", kept).insert("suppressed", suppressed)


def _line(lines, number):
    return lines[number - 1] if number and 0 < number <= len(lines) else ""


def _is_suppressed(finding, lines, marker=MARKER) -> bool:
    for number in (finding.line, finding.call_line):
        if marker.search(_line(lines, number)):
            return True
    above = _line(lines, finding.line - 1)
    return bool(_COMMENT_ONLY.match(above) and marker.search(above))
