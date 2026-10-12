"""Finding: one anonymous step, located in the source."""

from typing import NamedTuple, Optional


class Finding(NamedTuple):
    """An anonymous step at ``path:line:col`` (1-based line and column).

    ``call_line`` is the line of the enclosing ``add_*`` / Valve call, when it
    differs from ``line``: a suppression comment may sit on either.
    ``severity`` is ``"warning"`` for a finding that is reported and does not
    fail the run, unless the run is strict.
    """

    path: str
    line: int
    col: int
    rule: str
    slug: str
    message: str
    lang: str
    call_line: Optional[int] = None
    severity: Optional[str] = None

    def format(self) -> str:
        warning = "warning: " if self.severity == "warning" else ""
        return "%s:%d:%d  %s %s  %s%s" % (self.path, self.line, self.col, self.rule, self.slug, warning, self.message)
