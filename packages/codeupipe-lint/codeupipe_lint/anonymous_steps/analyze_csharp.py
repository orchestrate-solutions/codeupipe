"""AnalyzeCsharp: anonymous steps in C# files, by lexical scan.

The C# runtime detects every anonymous step (compiler-generated methods and
types); this gives the same feedback at
authoring time. A step is an argument of ``.AddFilter``, ``.AddTap``,
``.AddPipeline``, ``.AddParallel`` or ``new Valve(..)``. It is anonymous
when it is (or a local ``var``/typed declaration binds it to):

- CUP-A001 a lambda (``=>`` anywhere in the argument) or an anonymous
  method (``delegate (..) { .. }``), or the result of a method in this file
  declared to return ``Func<..>``, ``Action<..>`` or ``Predicate<..>``, or
  returning an adapter built around one (``return new Fn(p => ..)``);
- CUP-A002 a local function: declared inside a method body, or a function
  of the top-level statements (the compiler makes those local functions of
  the generated Main);
- CUP-A004 an anonymous type (``new { .. }``);
- CUP-A005 a plain ``new Pipeline()`` (or a chain on it), or the result of
  a method in this file declared to return ``Pipeline``.

C# has no local classes, so CUP-A003 does not apply.
"""

import re
from types import SimpleNamespace

from codeupipe import Payload

from .lexical import match_close, split_args
from .lexical_engine import scan
from .rules import ANONYMOUS_TYPE, LAMBDA, LOCAL_FUNCTION, PARSE_ERROR, UNNAMED_PIPELINE, make_finding

_KEYWORDS = {"if", "for", "foreach", "while", "switch", "catch", "using", "lock", "fixed", "return", "nameof",
             "typeof", "sizeof", "default", "new", "when", "await", "throw", "else", "base", "this"}
# A lambda or anonymous method as the first constructor argument: new Fn(p => ..).
_WRAPPED_LAMBDA = re.compile(r"\bnew\s+([\w.]+(?:<[^()]*>)?)\s*\(\s*(?:[A-Za-z_]\w*|\([^()]*\))\s*=>|"
                             r"\bnew\s+([\w.]+(?:<[^()]*>)?)\s*\(\s*delegate\b")
_DELEGATE_TYPE = re.compile(r"\b(?:Func|Action|Predicate|Converter)\s*<|\bFunc\b|\bAction\b")


def _kind_of(head, parent_kind):
    if re.match(r"^(?:\[[^\]]*\]\s*)*(?:[\w]+\s+)*?(?:class|struct|record|interface|enum)\s+\w", head):
        return "type"
    if re.match(r"^(?:\[[^\]]*\]\s*)*namespace\b", head):
        return "other"
    if ")" in head or "=>" in head or re.search(r"\b(?:get|set|init|add|remove|else|try|finally|do)$", head):
        return "code"
    return "other"


def _function_info(head):
    body = re.sub(r"^(?:\[[^\]]*\]\s*)+", "", head)
    depth = 0
    for i, c in enumerate(body):
        if c == "<":
            depth += 1
        elif c == ">":
            depth = max(0, depth - 1)
        elif c == "(" and depth == 0:
            m = re.search(r"([A-Za-z_]\w*)\s*(?:<[^()]*>)?\s*$", body[:i])
            if not m or m.group(1) in _KEYWORDS:
                return None
            ret = body[:m.start()].strip()
            if not ret or ret.endswith(("=", ".", "new")):
                return None
            return m.group(1), ret
    return None


def _elements(text):
    m = re.match(r"^(?:new\s*(?:[\w.<>]+\s*)?\[\s*\]\s*)?[\[{]", text)
    if not m:
        return None
    return split_args(text, m.end() - 1, match_close(text, m.end() - 1))


def _classify(text, ctx):
    t = text.strip()
    if re.match(r"^new\s+(?:[\w.]+\.)?Valve\s*\(", t):
        return None  # the Valve's own arguments are checked where it is constructed
    if re.match(r"^new\s*\{", t):
        return ANONYMOUS_TYPE, None, "an anonymous type (new { ... })"
    if re.search(r"\bdelegate\s*[({]", t):
        return LAMBDA, None, "an anonymous method (delegate)"
    if "=>" in t:
        return LAMBDA, None, "a lambda"
    if re.match(r"^new\s+(?:[\w.]+\.)?Pipeline\s*\(\s*\)", t):
        return UNNAMED_PIPELINE, None, "a plain new Pipeline()"
    if re.match(r"^[A-Za-z_]\w*$", t):
        got = ctx.binding(t)
        if got:
            return got[0], t, got[1]
        if ctx.is_bound(t):
            return None
        if ctx.local_function(t):
            return LOCAL_FUNCTION, t, "a local function declared inside %s" % ctx.local_function(t)
        function = ctx.function(t)
        if function is not None and function["parent_kind"] == "file":
            return LOCAL_FUNCTION, t, "a function of the top-level statements (compiled as a local function)"
        return None
    call = re.match(r"^([A-Za-z_]\w*)\s*(?:<[^()]*>)?\s*\(", t)
    if call and ctx.function(call.group(1)):
        name = call.group(1)
        ret = ctx.function(name)["ret"]
        ret_type = re.sub(r"^(?:(?:public|private|protected|internal|static|async|override|virtual|sealed|"
                          r"unsafe|extern|new|partial)\s+)*", "", ret)
        if _DELEGATE_TYPE.search(ret_type):
            return LAMBDA, None, "the result of %s(), which returns a delegate (%s)" % (name, ret_type)
        if re.match(r"^(?:[\w.]+\.)?Pipeline\??$", ret_type):
            return UNNAMED_PIPELINE, None, "the result of %s(), which returns a plain Pipeline" % name
        info = ctx.function(name)
        body = ctx.body(name)
        expression_bodied = info["span"] is not None or "=>" in info["head"]
        returned = [body] if expression_bodied else re.findall(r"\breturn\b([^;]*)", body)
        for text in returned:
            wrapped = _WRAPPED_LAMBDA.search(text)
            if wrapped:
                return (LAMBDA, None, "the result of %s(), which returns a lambda wrapped in %s"
                        % (name, wrapped.group(1) or wrapped.group(2)))
    return None


def _valve_role(index, count):
    return "Valve predicate" if index == count - 1 else "Valve inner filter"


def _method(names):
    return re.compile(r"\.\s*(?:%s)\s*(?:<[^()]*>)?\s*\(" % "|".join(names))


SPEC = SimpleNamespace(
    lang="csharp",
    kind_of=_kind_of,
    function_info=_function_info,
    methods_are_functions=True,
    expression_function_re=re.compile(
        r"(?<![\w.])(?P<ret>(?:[A-Za-z_][\w.]*(?:<[^;{}()=]*>)?\??\s+)+?)(?P<name>[A-Za-z_]\w*)\s*"
        r"(?:<[^;{}()]*>)?\s*\([^;{}]*\)\s*=>\s*"),
    local_type_re=re.compile(r"(?!x)x(?P<name>)"),
    local_function_re=re.compile(
        r"(?<![\w.])(?!(?:return|new|await|else|throw|case|yield|var)\b)"
        r"(?:(?:static|async|unsafe)\s+)*[A-Za-z_][\w.]*(?:<[^;{}()]*>)?\??\s+"
        r"(?P<name>[A-Za-z_]\w*)\s*(?:<[^;{}()]*>)?\s*\([^;{}]*\)\s*(?==>|\{)"),
    binding_re=re.compile(
        r"(?<![\w.])(?!(?:return|new|await|else|throw|case)\b)(?:var|[A-Za-z_][\w.]*(?:<[^;{}()=]*>)?\??)\s+"
        r"(?P<name>[A-Za-z_]\w*)\s*=(?![=>])\s*"),
    calls=[
        (_method(["AddFilter"]), lambda i, n: "Filter", False),
        (_method(["AddTap"]), lambda i, n: "Tap", False),
        (_method(["AddPipeline"]), lambda i, n: "Nested pipeline", False),
        (_method(["AddParallel"]), lambda i, n: "Parallel filter", True),
        (re.compile(r"\bnew\s+(?:[\w.]+\.)?Valve\s*\("), _valve_role, False),
    ],
    elements=_elements,
    named_arg_re=re.compile(r"([A-Za-z_]\w*)\s*:(?!:)\s*"),
    named_roles={"inner": "Valve inner filter", "predicate": "Valve predicate"},
    classify=_classify,
)


class AnalyzeCsharp:
    """Filter (sync).

    Input keys: ``files`` ({lang: [path]}), ``findings``.
    Output keys: ``findings`` with C# findings appended.
    """

    def call(self, payload: Payload) -> Payload:
        findings = list(payload.get("findings", []))
        for path in payload.get("files", {}).get("csharp", []):
            try:
                with open(path, encoding="utf-8-sig") as handle:
                    text = handle.read()
            except (OSError, UnicodeDecodeError) as error:
                findings.append(make_finding("csharp", path, 1, 1, PARSE_ERROR, "File",
                                             "could not be read (%s)" % error))
                continue
            findings.extend(scan(path, text, SPEC))
        return payload.insert("findings", findings)
