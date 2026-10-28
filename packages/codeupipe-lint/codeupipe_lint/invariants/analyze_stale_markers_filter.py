"""AnalyzeStaleMarkersFilter: CUP-I009, a warning: a comment that allows nothing.

A ``# cup: allow-...`` comment that allowed no finding stays when the code
that it was for is gone or has moved, or when its kind has a spelling error.
It then says that the code has an exception that it does not have.

Only a comment that starts with the marker counts, so text that names a
marker in a string or in the middle of a sentence is not reported. A
``cup: allow-anonymous`` comment is for the other linter
(``codeupipe_lint.anonymous_steps``) and is not looked at here.
"""

import io
import re
import tokenize

from codeupipe import Payload

from .rules import MARKER_ALLOWS_NOTHING, make_finding

_MARKER = re.compile(r"#+\s*cup:\s*(allow-[\w-]*)")
_OTHER_LINTER = ("allow-anonymous",)


class AnalyzeStaleMarkersFilter:
    """Filter (sync).

    Input keys: ``trees`` ({path: ast.Module}), ``findings``, ``used_markers``
    (from ApplySuppressionsFilter).
    Output keys: ``findings`` with CUP-I009 warnings appended.
    """

    def call(self, payload: Payload) -> Payload:
        used = {tuple(place) for place in payload.get("used_markers", [])}
        findings = list(payload.get("findings", []))
        for path in payload.get("trees", {}):
            for line, col, kind in self.markers_of(path):
                if (path, line) in used or kind in _OTHER_LINTER:
                    continue
                findings.append(make_finding(path, line, col, MARKER_ALLOWS_NOTHING,
                                             "The comment `cup: %s` allows nothing" % kind))
        return payload.insert("findings", findings)

    def markers_of(self, path):
        """``(line, col, kind)`` for each comment of the file that starts with a marker."""
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        except (OSError, tokenize.TokenError, SyntaxError):
            return []
        markers = []
        for token in tokens:
            match = _MARKER.match(token.string) if token.type == tokenize.COMMENT else None
            if match:
                markers.append((token.start[0], token.start[1] + 1, match.group(1)))
        return markers
