"""A small lexical toolkit for the languages with no parser on this side
(Rust, C++, Kotlin, C#). Stdlib only, heuristic by design: packages/codeupipe-lint/README.md
lists what it cannot see.

- ``strip_source`` blanks comments and string/char literal contents (same
  length, newlines kept), so positions still map to the original file.
- ``frames`` pairs every ``{`` with its ``}`` and asks a language hook what
  the block is: ``code`` (a function body, or any block inside one),
  ``type`` (a struct/class/impl body), or ``other``.
- ``split_args`` splits a call's argument list at top-level commas.
"""

import bisect
import re
from typing import Callable, List, NamedTuple, Optional, Tuple

_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {")", "]", "}"}


def _blank(chars: List[str], start: int, end: int) -> None:
    for i in range(start, end):
        if chars[i] != "\n":
            chars[i] = " "


def strip_source(text: str, lang: str) -> str:
    """Comments and literal contents blanked; quote characters kept."""
    chars = list(text)
    n = len(text)
    i = 0
    nested_comments = lang in ("rust", "kotlin")
    at_line_start = True
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if lang == "cpp" and at_line_start and c == "#":
            # preprocessor directive, with backslash continuations
            j = i
            while j < n and text[j] != "\n":
                if text[j] == "\\" and j + 1 < n and text[j + 1] == "\n":
                    j += 2
                    continue
                j += 1
            _blank(chars, i, j)
            i = j
            continue
        if c == "\n":
            at_line_start = True
            i += 1
            continue
        if not c.isspace():
            at_line_start = False
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            _blank(chars, i, j)
            i = j
            continue
        if c == "/" and nxt == "*":
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("*/", j):
                    depth -= 1
                    j += 2
                elif nested_comments and text.startswith("/*", j):
                    depth += 1
                    j += 2
                else:
                    j += 1
            _blank(chars, i, j)
            i = j
            continue
        # raw / verbatim strings
        if lang == "rust" and c in "rb" and re.match(r'(?:br|r)#*"', text[i:i + 12]) and not _ident_before(text, i):
            m = re.match(r'(?:br|r)(#*)"', text[i:])
            close = '"' + m.group(1)
            j = text.find(close, i + m.end())
            j = n if j < 0 else j + len(close)
            _blank(chars, i + m.end(), j - len(close))
            i = j
            continue
        if lang == "cpp" and c == "R" and nxt == '"' and not _ident_before(text, i):
            m = re.match(r'R"([^(\s]*)\(', text[i:])
            if m:
                close = ")" + m.group(1) + '"'
                j = text.find(close, i + m.end())
                j = n if j < 0 else j + len(close)
                _blank(chars, i + 2, j - 1)
                i = j
                continue
        if lang in ("kotlin", "csharp") and text.startswith('"""', i):
            j = text.find('"""', i + 3)
            j = n if j < 0 else j + 3
            _blank(chars, i + 3, j - 3)
            i = j
            continue
        if lang == "csharp" and c in "@$" and (nxt == '"' or text[i + 1:i + 3] in ('@"', '$"')):
            k = i
            while text[k] in "@$":
                k += 1
            verbatim = "@" in text[i:k]
            j = k + 1
            while j < n:
                if text[j] == "\\" and not verbatim:
                    j += 2
                    continue
                if text[j] == '"':
                    if verbatim and j + 1 < n and text[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            _blank(chars, k + 1, j)
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"' and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            _blank(chars, i + 1, min(j, n))
            i = j + 1
            continue
        if c == "'":
            m = re.match(r"'(\\.[^']*|[^\\'\n])'", text[i:i + 12])
            digit_separator = lang == "cpp" and i > 0 and text[i - 1].isalnum() and nxt.isalnum()
            if m and not digit_separator:
                _blank(chars, i + 1, i + m.end() - 1)
                i += m.end()
                continue
            i += 1  # a Rust lifetime / label, or a C++ digit separator
            continue
        i += 1
    return "".join(chars)


def _ident_before(text: str, i: int) -> bool:
    return i > 0 and (text[i - 1].isalnum() or text[i - 1] == "_")


def match_close(text: str, open_index: int) -> int:
    """Index of the bracket closing ``text[open_index]`` (in stripped text), or len(text)."""
    stack = []
    for j in range(open_index, len(text)):
        c = text[j]
        if c in _OPEN:
            stack.append(_OPEN[c])
        elif c in _CLOSE:
            if not stack or stack[-1] != c:
                return len(text)
            stack.pop()
            if not stack:
                return j
    return len(text)


def split_args(text: str, open_index: int, close_index: int) -> List[Tuple[int, int]]:
    """(start, end) spans of the top-level, comma-separated arguments, trimmed."""
    spans = []
    depth = 0
    start = open_index + 1
    for j in range(open_index + 1, close_index + 1):
        c = text[j] if j < close_index else ","
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth -= 1
        elif c == "," and depth == 0:
            s, e = start, j
            while s < e and text[s].isspace():
                s += 1
            while e > s and text[e - 1].isspace():
                e -= 1
            if e > s:
                spans.append((s, e))
            start = j + 1
    return spans


def line_starts(text: str) -> List[int]:
    return [0] + [m.end() for m in re.finditer(r"\n", text)]


def line_col(starts: List[int], offset: int) -> Tuple[int, int]:
    """1-based (line, column) of ``offset``."""
    line = bisect.bisect_right(starts, offset) - 1
    return line + 1, offset - starts[line] + 1


class _Frame(NamedTuple):
    open: int
    close: int
    kind: str
    head: str
    parent: Optional[int]


def head_before(text: str, index: int, newline_separates: bool = False) -> str:
    """The statement text before ``text[index]``, back to the previous ``;``, ``{`` or ``}``
    (or newline, outside brackets, when ``newline_separates``: Kotlin)."""
    j = index - 1
    depth = 0
    while j >= 0:
        c = text[j]
        if c in ")]":
            depth += 1
        elif c in "([":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and (c in ";{}" or (newline_separates and c == "\n" and text[j + 1:index].strip())):
            break
        j -= 1
    return text[j + 1:index].strip()


def frames(text: str, kind_of: Callable[[str, str], str], newline_separates: bool = False) -> List[_Frame]:
    """Every ``{ ... }`` block, in order of its ``{``.

    ``kind_of(head, parent_kind)`` names the block ("code", "type", "other");
    ``parent_kind`` is "file" at the top level.
    """
    result: List[_Frame] = []
    stack: List[int] = []
    pending = {}
    for j, c in enumerate(text):
        if c == "{":
            parent = stack[-1] if stack else None
            parent_kind = result[parent].kind if parent is not None else "file"
            head = head_before(text, j, newline_separates)
            kind = "code" if parent_kind == "code" and not _is_type_head(head) else kind_of(head, parent_kind)
            result.append(_Frame(j, len(text), kind, head, parent))
            stack.append(len(result) - 1)
        elif c == "}" and stack:
            index = stack.pop()
            pending[index] = j
    return [f._replace(close=pending.get(i, len(text))) for i, f in enumerate(result)]


_TYPE_HEAD = re.compile(r"^(?:[\w\s:<>,()\[\]]*?\s)?(?:struct|class|union|enum|impl|trait|interface|object|record)\b"
                        r"(?![^\n]*=>)")


def _is_type_head(head: str) -> bool:
    return bool(_TYPE_HEAD.match(head)) and "=" not in head.split("{")[0].split("(")[0]


def enclosing(all_frames: List[_Frame], offset: int) -> List[int]:
    """Indexes of the frames containing ``offset``, outermost first."""
    return [i for i, f in enumerate(all_frames) if f.open < offset < f.close]


def function_scope(all_frames: List[_Frame], offset: int) -> Optional[int]:
    """The outermost ``code`` frame containing ``offset`` (a function body), or None."""
    for i in enclosing(all_frames, offset):
        if all_frames[i].kind == "code":
            return i
    return None


def expression_end(text: str, start: int, newline_ends: bool = False) -> int:
    """End of the expression starting at ``start``: the first top-level ``;``
    (or newline, for Kotlin, unless the next line continues with ``.``/``?.``),
    or an unmatched closing bracket."""
    depth = 0
    j = start
    n = len(text)
    while j < n:
        c = text[j]
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            if depth == 0:
                return j
            depth -= 1
        elif depth == 0 and c == ";":
            return j
        elif depth == 0 and newline_ends and c == "\n":
            rest = text[j + 1:].lstrip()
            if not (rest.startswith(".") or rest.startswith("?.")):
                return j
        j += 1
    return n


def receiver_root(text: str, dot_index: int) -> str:
    """The start of the method chain ending just before ``text[dot_index]``
    (a ``.``): for ``Parallel::new().with(A).with(B)`` at the last ``.``,
    ``Parallel::new``. Balanced ``(..)`` groups are skipped."""
    j = dot_index - 1
    root = ""
    while j >= 0:
        while j >= 0 and text[j].isspace():
            j -= 1
        if j >= 0 and text[j] == ")":
            depth = 0
            while j >= 0:
                if text[j] == ")":
                    depth += 1
                elif text[j] == "(":
                    depth -= 1
                    if depth == 0:
                        break
                j -= 1
            j -= 1
        end = j + 1
        while j >= 0 and (text[j].isalnum() or text[j] in "_:"):
            j -= 1
        root = text[j + 1:end]
        k = j
        while k >= 0 and text[k].isspace():
            k -= 1
        if k >= 0 and text[k] == "." and root:
            j = k - 1
            continue
        return root
    return root
