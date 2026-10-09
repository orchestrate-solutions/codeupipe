"""AnalyzeKotlin: anonymous steps in Kotlin files, by lexical scan.

The Kotlin runtime detects every anonymous step (synthetic and local
classes); this gives the same feedback at
authoring time. A step is an argument of ``addFilter``, ``addTap``,
``addPipeline``, ``addParallel`` (receiver optional, so ``init { addFilter(..) }``
counts) or ``Valve(..)``, including a trailing lambda. It is anonymous when
it is (or a ``val``/``var`` binds it to):

- CUP-A001 a lambda (``{ p -> p }``, a trailing lambda), a SAM lambda
  (``Filter { .. }``), an anonymous function (``fun(p: Payload) = p``), or
  the result of a function in this file whose declared return type is a
  function type or whose returned expression is one of these;
- CUP-A002 a ``fun`` declared inside a function body;
- CUP-A003 an instance of a class declared inside a function body;
- CUP-A004 an anonymous object (``object : Filter { .. }``);
- CUP-A005 a plain ``Pipeline()`` (or a chain on it), or the result of a
  function in this file declared to return ``Pipeline``.
"""

import re
from types import SimpleNamespace

from codeupipe import Payload

from .lexical import expression_end, match_close, split_args
from .lexical_engine import scan
from .rules import (ANONYMOUS_TYPE, LAMBDA, LOCAL_FUNCTION, LOCAL_TYPE, PARSE_ERROR, UNNAMED_PIPELINE,
                    make_finding)

_TYPE_HEAD = re.compile(r"^(?:[\w@()\s]*\s)?(?:class|interface|object)\b(?!\s*:)")
_SAM = re.compile(r"^(?:[\w.]+\.)?[A-Z]\w*(?:<[^{}]*>)?\s*\{")
_RETURNED = re.compile(r"(?:^|->|=|\breturn\b)\s*(?P<expr>(?:[\w.]+\.)?[A-Z]\w*(?:<[^{}]*>)?\s*\{|\{|object\s*:)")


def _kind_of(head, parent_kind):
    if _TYPE_HEAD.match(head) and "=" not in head.split("(")[0]:
        return "type"
    return "code"


def _function_info(head):
    m = re.search(r"\bfun\s+(?:<[^()]*>\s*)?(?:[\w.]+\.)?(`[^`\n]+`|[A-Za-z_]\w*)\s*\(", head)
    if not m:
        return None
    close = match_close(head, m.end() - 1)
    rest = head[close + 1:]
    ret = ""
    rm = re.match(r"\s*:\s*([^=]*)", rest)
    if rm:
        ret = rm.group(1)
    return m.group(1), ret + ("=" + rest.split("=", 1)[1] if "=" in rest else "")


def _elements(text):
    m = re.match(r"^(?:listOf|arrayOf|mutableListOf)\s*(?:<[^()]*>)?\s*\(", text)
    if not m:
        return None
    return split_args(text, m.end() - 1, match_close(text, m.end() - 1))


def _anonymous_expression(t):
    if t.startswith("{"):
        return LAMBDA, None, "a lambda"
    if re.match(r"^object\s*:", t):
        return ANONYMOUS_TYPE, None, "an anonymous object (object : ...)"
    if re.match(r"^fun\s*\(", t):
        return LAMBDA, None, "an anonymous function"
    if _SAM.match(t) and not re.match(r"^Pipeline\b", t):
        return LAMBDA, None, "a lambda (%s { ... })" % re.match(r"^[\w.]+", t).group(0)
    return None


def _returned(name, ctx):
    info = ctx.function(name)
    ret, has_expression_body, expression = info["ret"].partition("=")
    if "->" in ret:
        return LAMBDA, "a function (%s)" % ret.strip()
    if re.match(r"^\s*(?:[\w.]+\.)?Pipeline\s*\??\s*$", ret):
        return UNNAMED_PIPELINE, "a plain Pipeline"
    body = ctx.body(name)
    if has_expression_body:
        # The frame is the expression's own block: the lambda itself
        # (`= { .. }`, `= Filter { .. }`), or a `when`/`if` whose branches return.
        expression = expression.strip()
        if not expression or _SAM.match(expression + " {"):
            return LAMBDA, "a lambda"
        search = [body]
    else:
        search = [body[m.end():expression_end(body, m.end(), True)] for m in re.finditer(r"\breturn\b", body)]
    fctx = ctx.function_ctx(name)
    for text in search:
        m = _RETURNED.search(text)
        if m:
            got = _anonymous_expression(m.group("expr").strip())
            if got:
                return got[0], got[2]
        local = re.match(r"^\s*([A-Za-z_]\w*)\s*\(", text)
        if local and fctx is not None and fctx.local_type(local.group(1)):
            return LOCAL_TYPE, "an instance of %s, a class declared inside %s()" % (local.group(1), name)
    return None


def _classify(text, ctx):
    t = text.strip()
    got = _anonymous_expression(t)
    if got:
        return got
    if re.match(r"^(?:[\w.]+\.)?Pipeline\s*\(\s*\)", t):
        return UNNAMED_PIPELINE, None, "a plain Pipeline()"
    if re.match(r"^[A-Za-z_]\w*$", t):
        got = ctx.binding(t)
        if got:
            return got[0], t, got[1]
        if ctx.is_bound(t):
            return None
        if ctx.local_function(t):
            return LOCAL_FUNCTION, t, "a function declared inside %s" % ctx.local_function(t)
        if ctx.local_type(t):
            return LOCAL_TYPE, t, "a class declared inside %s" % ctx.local_type(t)
        return None
    call = re.match(r"^([A-Za-z_]\w*)\s*(?:<[^()]*>)?\s*\(", t)
    if call:
        name = call.group(1)
        if ctx.local_type(name):
            return LOCAL_TYPE, None, "an instance of %s, a class declared inside %s" % (name, ctx.local_type(name))
        if ctx.function(name):
            got = _returned(name, ctx)
            if got:
                return got[0], None, "the result of %s(), which returns %s" % (name, got[1])
    return None


def _valve_role(index, count):
    return "Valve predicate" if index == count - 1 else "Valve inner filter"


def _method(names):
    return re.compile(r"(?<![\w])(?<!fun )(?:%s)\s*[({]" % "|".join(names))


SPEC = SimpleNamespace(
    lang="kotlin",
    methods_are_functions=True,
    kind_of=_kind_of,
    function_info=_function_info,
    local_type_re=re.compile(r"\b(?:class|interface|object)\s+(?P<name>[A-Za-z_]\w*)"),
    local_function_re=re.compile(r"\bfun\s+(?:<[^()]*>\s*)?(?P<name>[A-Za-z_]\w*)\s*\("),
    binding_re=re.compile(r"\b(?:val|var)\s+(?P<name>[A-Za-z_]\w*)\s*(?::[^=\n]+)?=(?!=)\s*"),
    newline_ends=True,
    trailing_lambda=True,
    calls=[
        (_method(["addFilter"]), lambda i, n: "Filter", False),
        (_method(["addTap"]), lambda i, n: "Tap", False),
        (_method(["addPipeline"]), lambda i, n: "Nested pipeline", False),
        (_method(["addParallel"]), lambda i, n: "Parallel filter", True),
        (re.compile(r"(?<![\w.])(?<!class )(?<!fun )Valve\s*\("), _valve_role, False),
    ],
    elements=_elements,
    named_arg_re=re.compile(r"([A-Za-z_]\w*)\s*=(?!=)\s*"),
    named_roles={"inner": "Valve inner filter", "predicate": "Valve predicate"},
    classify=_classify,
)


class AnalyzeKotlin:
    """Filter (sync).

    Input keys: ``files`` ({lang: [path]}), ``findings``.
    Output keys: ``findings`` with Kotlin findings appended.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path in payload.get("files", {}).get("kotlin", []):
            try:
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
            except (OSError, UnicodeDecodeError) as error:
                findings.append(make_finding("kotlin", path, 1, 1, PARSE_ERROR, "File",
                                             "could not be read (%s)" % error))
                continue
            findings.extend(scan(path, text, SPEC))
        return payload.insert("findings", findings)
