"""AnalyzeCpp: anonymous steps in C++ files, by lexical scan.

There is no C++ parser on the Python side, so this is a heuristic over
source with comments, literals and preprocessor lines blanked (lexical.py).
A step is an argument of ``.add_filter`` / ``->add_filter``, ``add_tap``,
``add_pipeline``, ``add_parallel``, or of a Valve construction
(``std::make_unique<Valve>(..)``, ``std::make_shared<Valve>(..)``,
``Valve(..)``). It is anonymous when:

- CUP-A001 a lambda appears anywhere in it (``make_filter([](..) {..})``),
  or it is a local ``auto`` bound to one, or the result of a function in
  this file that returns a lambda;
- CUP-A003 it names a struct/class/union defined inside a function body
  (``std::make_unique<Local>()``, ``Local{}``);
- CUP-A005 it is a plain ``Pipeline()`` / ``Pipeline{}``, a variable
  declared as ``Pipeline``, or the result of a function in this file
  declared to return ``Pipeline``;
- CUP-A007 it names a free function (by ``&name``, ``name``, or qualified)
  defined at namespace scope in this file, or takes the address of a
  qualified name (``&ns::fn``): C++ filters must be types.

A Valve construction passed as a step is not itself flagged; its own
arguments are checked. For C++, a struct defined inside a function has an
unqualified name at runtime, so this is the only check for CUP-A003.
"""

import re
from types import SimpleNamespace

from codeupipe import Payload

from .lexical import match_close, split_args
from .lexical_engine import scan, unwrap_calls
from .rules import FREE_FUNCTION, LAMBDA, LOCAL_TYPE, PARSE_ERROR, UNNAMED_PIPELINE, make_finding

_KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "sizeof", "decltype", "alignof", "static_assert",
             "requires", "noexcept", "throw", "new", "delete", "operator"}
_MOVE = re.compile(r"^(?:std\s*::\s*)?(?:move|forward\s*<[^()]*>)\s*\(")
_VALVE = re.compile(r"^(?:(?:std\s*::\s*)?make_(?:unique|shared)\s*<\s*(?:\w+\s*::\s*)*Valve\s*>|"
                    r"(?:\w+\s*::\s*)*Valve)\s*[({]")
# A lambda introducer: [captures] then (params), specifiers, -> ret, or the body.
_LAMBDA = re.compile(r"(?<![\w\)\]>\s])\s*\[[^\[\]]*\]\s*(?:\((?:[^()]|\([^()]*\))*\))?\s*"
                     r"(?:(?:mutable|constexpr|noexcept|static)\s*)*(?:->\s*[^{;]+?)?\s*\{")
_PLAIN_PIPELINE = re.compile(r"^(?:\w+\s*::\s*)*Pipeline\s*(?:\(\s*\)|\{\s*\}|[A-Za-z_]\w*)")


def _has_lambda(text):
    # (?<!...) above cannot see a match at position 0 preceded by nothing; pad.
    return bool(_LAMBDA.search("(" + text))


def _kind_of(head, parent_kind):
    body = re.sub(r"^template\s*<.*?>\s*", "", head, flags=re.S)
    if re.match(r"^(?:inline\s+)?namespace\b|^extern\s+\"", body):
        return "other"
    if re.match(r"^(?:\[\[.*?\]\]\s*)?(?:struct|class|union|enum)\b", body) and "=" not in body.split("(")[0]:
        return "type"
    if ")" in body or body.rstrip().endswith("]"):
        return "code"
    return "other"


def _function_info(head):
    body = re.sub(r"^template\s*<.*?>\s*", "", head, flags=re.S)
    depth = 0
    for i, c in enumerate(body):
        if c == "<":
            depth += 1
        elif c == ">":
            depth = max(0, depth - 1)
        elif c == "(" and depth == 0:
            m = re.search(r"((?:[A-Za-z_]\w*\s*::\s*)*~?[A-Za-z_]\w*)\s*$", body[:i])
            if not m or m.group(1) in _KEYWORDS or body[:m.start()].rstrip().endswith(("]", "=")):
                return None
            name = re.sub(r"\s+", "", m.group(1))
            if name.split("::")[-1] in _KEYWORDS:
                return None
            ret = body[:m.start()].strip()
            close = match_close(body, i)
            trailing = body[close + 1:]
            if "->" in trailing:
                ret += " " + trailing.split("->", 1)[1]
            return name, ret
    return None


def _elements(text):
    m = re.match(r"^(?:[\w:]+\s*<[^()]*>\s*)?\{", text)
    if not m:
        return None
    return split_args(text, m.end() - 1, match_close(text, m.end() - 1))


def _returns_lambda(name, ctx):
    body = ctx.body(name)
    for m in re.finditer(r"\breturn\b", body):
        end = body.find(";", m.end())
        if _has_lambda(body[m.end():end if end >= 0 else len(body)]):
            return True
    return False


def _classify(text, ctx):
    t = unwrap_calls(text, _MOVE)
    t = re.sub(r"^\*\s*", "", t)
    if _VALVE.match(t):
        return None  # the Valve's own arguments are checked where it is constructed
    if _has_lambda(t):
        return LAMBDA, None, "a lambda"
    if _PLAIN_PIPELINE.match(t):
        return UNNAMED_PIPELINE, None, "a plain Pipeline"
    ident = re.match(r"^[A-Za-z_]\w*$", t)
    if ident:
        got = ctx.binding(t)
        if got:
            return got[0], t, got[1]
        if ctx.is_bound(t):
            return None
    for m in re.finditer(r"(?<![\w.>])(&\s*)?((?:[A-Za-z_]\w*\s*::\s*)*)([A-Za-z_]\w*)\b(?!\s*[(<:])", t):
        amp, qualifier, name = m.group(1), m.group(2), m.group(3)
        where = ctx.local_type(name)
        if where and not qualifier:
            return LOCAL_TYPE, None, "a %s, a type defined inside %s" % (name, where)
        function = ctx.function(name)
        if function is not None and name not in ("main",):
            return FREE_FUNCTION, None, "the free function %s%s" % (re.sub(r"\s", "", qualifier), name)
        if amp and qualifier and not ctx.is_bound(name):
            return FREE_FUNCTION, None, "a pointer to %s%s, a function" % (re.sub(r"\s", "", qualifier), name)
    call = re.match(r"^((?:[A-Za-z_]\w*\s*::\s*)*)([A-Za-z_]\w*)\s*\(", t)
    if call and not call.group(1):
        name = call.group(2)
        function = ctx.function(name)
        if function is not None:
            if re.search(r"(?:^|[^\w:])Pipeline\s*&?$", function["ret"].strip()):
                return UNNAMED_PIPELINE, None, "the result of %s(), which returns a plain Pipeline" % name
            if _returns_lambda(name, ctx):
                return LAMBDA, None, "the result of %s(), which returns a lambda" % name
    return None


def _valve_role(index, count):
    return "Valve predicate" if index == count - 1 else "Valve inner filter"


def _method(names):
    return re.compile(r"(?:\.|->)\s*(?:%s)\s*(?:<[^()]*>)?\s*\(" % "|".join(names))


SPEC = SimpleNamespace(
    lang="cpp",
    kind_of=_kind_of,
    function_info=_function_info,
    local_type_re=re.compile(r"\b(?:struct|class|union)\s+(?P<name>[A-Za-z_]\w*)\s*(?:final\s*)?(?=[:{])"),
    local_function_re=None,
    binding_re=[
        re.compile(r"\b(?:const\s+)?auto\s*[&*]{0,2}\s*(?P<name>[A-Za-z_]\w*)\s*=(?!=)\s*"),
        re.compile(r"(?<![\w:])(?=(?:\w+::)*Pipeline\s+(?P<name>[A-Za-z_]\w*)\s*[;{=])"),
    ],
    calls=[
        (_method(["add_filter"]), lambda i, n: "Filter", False),
        (_method(["add_tap"]), lambda i, n: "Tap", False),
        (_method(["add_pipeline"]), lambda i, n: "Nested pipeline", False),
        (_method(["add_parallel"]), lambda i, n: "Parallel filter", True),
        (re.compile(r"(?:std\s*::\s*)?make_(?:unique|shared)\s*<\s*(?:\w+\s*::\s*)*Valve\s*>\s*\("),
         _valve_role, False),
        (re.compile(r"(?<![\w:<])(?<!class )(?<!struct )(?<!new )(?:\w+\s*::\s*)*Valve\s*\("), _valve_role, False),
    ],
    elements=_elements,
    classify=_classify,
)


class AnalyzeCpp:
    """Filter (sync).

    Input keys: ``files`` ({lang: [path]}), ``findings``.
    Output keys: ``findings`` with C++ findings appended.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path in payload.get("files", {}).get("cpp", []):
            try:
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
            except (OSError, UnicodeDecodeError) as error:
                findings.append(make_finding("cpp", path, 1, 1, PARSE_ERROR, "File", "could not be read (%s)" % error))
                continue
            findings.extend(scan(path, text, SPEC))
        return payload.insert("findings", findings)
