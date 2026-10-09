"""AnalyzeRust: anonymous steps in Rust files, by lexical scan.

There is no Rust parser on the Python side, so this is a heuristic over
source with comments and literals blanked (lexical.py). A step is an
argument of ``.add_filter``, ``.add_boxed_filter``, ``.add_stream_filter``,
``.add_tap``, ``.add_pipeline``, ``.add_parallel`` (elements of ``vec![..]``),
``.with(..)`` on a ``Parallel::new()`` chain, or ``Valve::new``, looking through ``Box::new``/``Arc::new``/``Rc::new`` and
``&``. It is anonymous when it is (or a ``let`` in the same function binds
it to):

- CUP-A001 a closure (``|..| ..``, ``move |..|``), or the result of a
  function in this file returning ``impl Fn*`` / ``Box<dyn Fn*>``;
- CUP-A002 a ``fn`` item declared inside a function body;
- CUP-A003 a value of a struct/enum/union declared inside a function body
  (``Local``, ``Local {..}``, ``Local(..)``, ``Local::new()``), or the
  result of a function in this file whose tail/return mentions one;
- CUP-A005 ``Pipeline::new()`` (or a builder chain on it), or the result
  of a function in this file whose return type names ``Pipeline``.

For Rust, a struct declared inside a function looks like a module path at
runtime (``main::Local``), so this is the only check for CUP-A003.
"""

import re
from types import SimpleNamespace

from codeupipe import Payload

from .lexical import match_close, receiver_root, split_args
from .lexical_engine import leading_path, scan, unwrap_calls
from .rules import LAMBDA, LOCAL_FUNCTION, LOCAL_TYPE, PARSE_ERROR, UNNAMED_PIPELINE, make_finding

_WRAPPERS = re.compile(r"^(?:(?:\w+\s*::\s*)*(?:Box|Arc|Rc)\s*::\s*new|Some|Ok)\s*\(")
_CLOSURE = re.compile(r"^(?:async\s+)?(?:move\s+)?\|")
_TRAILING = re.compile(r"(?:\?|\.unwrap\(\s*\)|\.clone\(\s*\)|\.expect\([^()]*\)|\.into\(\s*\))+$")
_FN_TRAIT = re.compile(r"\b(?:impl|dyn)\s+(?:Fn|FnMut|FnOnce)\b")


def _kind_of(head, parent_kind):
    if re.search(r"\bfn\b", head):
        return "code"
    if re.match(r"^(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?(?:impl|trait|struct|enum|union)\b", head):
        return "type"
    return "other"


def _function_info(head):
    m = re.search(r"\bfn\s+([A-Za-z_]\w*)\s*(?:<[^()]*>)?\s*\(", head)
    if not m:
        return None
    close = match_close(head, m.end() - 1)
    rest = head[close + 1:]
    ret = rest.split("->", 1)[1] if "->" in rest else ""
    return m.group(1), re.split(r"\bwhere\b", ret)[0]


def _elements(text):
    m = re.match(r"^(?:vec\s*!\s*)?\[", text)
    if not m:
        return None
    open_index = m.end() - 1
    return split_args(text, open_index, match_close(text, open_index))


def _returned_local_type(name, ctx):
    fctx = ctx.function_ctx(name)
    if fctx is None:
        return None
    body = ctx.body(name)
    depth, last = 0, -1
    for i, c in enumerate(body):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            last = i
    returned = [body[last + 1:]] + re.findall(r"\breturn\b([^;]*)", body)
    for text in returned:
        for ident in re.findall(r"\b[A-Za-z_]\w*", text):
            where = fctx.local_type(ident)
            if where:
                return ident, where
    return None


def _classify(text, ctx):
    t = unwrap_calls(text, _WRAPPERS)
    t = re.sub(r"^&\s*(?:mut\s+)?", "", t).strip()
    if _CLOSURE.match(t):
        return LAMBDA, None, "a closure"
    t = _TRAILING.sub("", t).strip()
    path, rest = leading_path(t)
    if not path:
        return None
    segments = [s.strip() for s in re.split(r"::|\.", path)]
    rest = rest.strip()
    joined = "::".join(segments)
    if (joined == "Pipeline::new" or joined.endswith("::Pipeline::new")) and rest.startswith("("):
        return UNNAMED_PIPELINE, None, "a plain Pipeline::new()"
    first = segments[0]
    local_type = ctx.local_type(first)
    if len(segments) == 1 and "::" not in path and "." not in path:
        if not rest or rest.startswith("."):
            got = ctx.binding(first)
            if got and (not rest or got[0] == UNNAMED_PIPELINE):
                return got[0], first, got[1]
            if not rest and ctx.local_function(first):
                return LOCAL_FUNCTION, first, "a fn declared inside %s" % ctx.local_function(first)
        if local_type and (not rest or rest[0] in "({."):
            return LOCAL_TYPE, None, "a value of %s, a type declared inside %s" % (first, local_type)
        if rest.startswith("(") and ctx.function(first):
            ret = ctx.function(first)["ret"]
            if _FN_TRAIT.search(ret):
                return LAMBDA, None, "the result of %s(), which returns a closure (%s)" % (first, ret.strip())
            if re.search(r"\bPipeline\b", ret):
                return UNNAMED_PIPELINE, None, "the result of %s(), which returns a plain Pipeline" % first
            local = _returned_local_type(first, ctx)
            if local:
                return (LOCAL_TYPE, None, "the result of %s(), which returns a value of %s, a type declared inside %s"
                        % (first, local[0], local[1]))
        return None
    if local_type and "." not in path:
        return LOCAL_TYPE, None, "a value of %s, a type declared inside %s" % (first, local_type)
    return None


def _on_parallel(stripped, start):
    """``.with(..)`` counts only on a ``Parallel::new()`` builder chain."""
    return re.search(r"(?:^|::)Parallel::new$", re.sub(r"\s", "", receiver_root(stripped, start))) is not None


def _valve_role(index, count):
    return "Valve predicate" if index == count - 1 else "Valve inner filter"


def _method(names):
    return re.compile(r"\.\s*(?:%s)\s*(?:::\s*<[^()]*>\s*)?\(" % "|".join(names))


SPEC = SimpleNamespace(
    lang="rust",
    kind_of=_kind_of,
    function_info=_function_info,
    local_type_re=re.compile(r"\b(?:struct|enum|union)\s+(?P<name>[A-Za-z_]\w*)"),
    local_function_re=re.compile(r"\bfn\s+(?P<name>[A-Za-z_]\w*)"),
    binding_re=re.compile(r"\blet\s+(?:mut\s+)?(?P<name>[A-Za-z_]\w*)\s*(?::[^=;]+)?=(?!=)\s*"),
    calls=[
        (_method(["add_filter", "add_boxed_filter", "add_stream_filter"]), lambda i, n: "Filter", False),
        (_method(["add_tap"]), lambda i, n: "Tap", False),
        (_method(["add_pipeline"]), lambda i, n: "Nested pipeline", False),
        (_method(["add_parallel"]), lambda i, n: "Parallel filter", True),
        (re.compile(r"\bValve\s*::\s*new\s*\("), _valve_role, False),
        (_method(["with"]), lambda i, n: "Parallel filter", False, _on_parallel),
    ],
    elements=_elements,
    classify=_classify,
)


class AnalyzeRust:
    """Filter (sync).

    Input keys: ``files`` ({lang: [path]}), ``findings``.
    Output keys: ``findings`` with Rust findings appended.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path in payload.get("files", {}).get("rust", []):
            try:
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
            except (OSError, UnicodeDecodeError) as error:
                findings.append(make_finding("rust", path, 1, 1, PARSE_ERROR, "File", "could not be read (%s)" % error))
                continue
            findings.extend(scan(path, text, SPEC))
        return payload.insert("findings", findings)
