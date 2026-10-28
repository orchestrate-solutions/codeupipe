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
    Output keys: ``findings`` (kept), ``suppressed`` (dropped), ``used_markers``
    (the place of each comment that allowed a finding, as ``(path, line)``).
    ``marker`` is the comment that suppresses; other linters pass their own.
    """

    def __init__(self, marker=MARKER):
        self.marker = marker

    def call(self, payload: Payload) -> Payload:
        cache = {}
        kept, suppressed, used = [], [], set()
        for finding in payload.get("findings", []):
            lines = cache.get(finding.path)
            if lines is None:
                try:
                    with open(finding.path, encoding="utf-8", errors="replace") as handle:
                        lines = handle.read().splitlines()
                except OSError:
                    lines = []
                cache[finding.path] = lines
            places = ApplySuppressionsFilter._marker_lines(finding, lines, self.marker)
            used.update((finding.path, place) for place in places)
            (suppressed if places else kept).append(finding)
        return (payload.insert("findings", kept).insert("suppressed", suppressed)
                .insert("used_markers", sorted(used)))

    @staticmethod
    def _line(lines, number):
        return lines[number - 1] if number and 0 < number <= len(lines) else ""

    @staticmethod
    def _marker_lines(finding, lines, marker=MARKER):
        """The lines of the comments that allow this finding. Empty when none does."""
        places = [number for number in (finding.line, finding.call_line) if marker.search(ApplySuppressionsFilter._line(lines, number))]
        above = ApplySuppressionsFilter._line(lines, finding.line - 1)
        if _COMMENT_ONLY.match(above) and marker.search(above):
            places.append(finding.line - 1)
        return places


def _is_suppressed(finding, lines, marker=MARKER) -> bool:
    return bool(ApplySuppressionsFilter._marker_lines(finding, lines, marker))
