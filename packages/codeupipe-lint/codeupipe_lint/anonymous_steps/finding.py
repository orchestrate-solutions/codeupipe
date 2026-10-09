"""Finding: one anonymous step, located in the source."""

from typing import NamedTuple, Optional


class Finding(NamedTuple):
    """An anonymous step at ``path:line:col`` (1-based line and column).

    ``call_line`` is the line of the enclosing ``add_*`` / Valve call, when it
    differs from ``line``: a suppression comment may sit on either.
    """

    path: str
    line: int
    col: int
    rule: str
    slug: str
    message: str
    lang: str
    call_line: Optional[int] = None

    def format(self) -> str:
        return "%s:%d:%d  %s %s  %s" % (self.path, self.line, self.col, self.rule, self.slug, self.message)
