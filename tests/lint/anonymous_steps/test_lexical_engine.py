"""lexical_engine.scan with a toy language spec."""

import re
from types import SimpleNamespace

from codeupipe_lint.anonymous_steps.lexical_engine import leading_path, scan, unwrap_calls


def _classify(text, ctx):
    if text.startswith("{"):
        return "CUP-A001", None, "a block lambda"
    if text == "LAMBDA":
        return "CUP-A001", None, "a lambda"
    if re.match(r"^\w+$", text):
        got = ctx.binding(text)
        if got:
            return got[0], text, got[1]
        if ctx.local_type(text):
            return "CUP-A003", text, "local"
    return None


SPEC = SimpleNamespace(
    lang="kotlin",
    kind_of=lambda head, parent: "code" if head.startswith("fun") else "other",
    function_info=lambda head: (re.match(r"fun (\w+)", head).group(1), "") if head.startswith("fun") else None,
    local_type_re=re.compile(r"\bclass (?P<name>\w+)"),
    local_function_re=None,
    binding_re=re.compile(r"\bval (?P<name>\w+) = "),
    newline_ends=True,
    calls=[(re.compile(r"\.add\s*[({]"), lambda i, n: "Filter", False)],
    elements=lambda text: None,
    trailing_lambda=True,
    classify=_classify,
)

SOURCE = """\
val top = LAMBDA
fun main() {
    class Local
    val same = LAMBDA
    val mixed = LAMBDA
    val mixed = other
    p.add(top)
    p.add(same)
    p.add(mixed)
    p.add(Local)
    p.add("x") { it }
    p.add { it }
}
fun other() {
    p.add(Local)
}
"""


def test_scan_resolves_bindings_scopes_and_trailing_lambdas():
    found = scan("toy.kt", SOURCE, SPEC)
    got = sorted((f.line, f.rule) for f in found)
    assert got == [(7, "CUP-A001"), (8, "CUP-A001"), (10, "CUP-A003"), (11, "CUP-A001"), (12, "CUP-A001")]
    top = [f for f in found if f.line == 7][0]
    assert top.message.startswith("Filter `top` is a lambda.")


def test_unwrap_calls_and_leading_path():
    wrappers = re.compile(r"^Box::new\(")
    assert unwrap_calls("Box::new(Box::new(x))", wrappers) == "x"
    assert unwrap_calls("Box::new(x).y()", wrappers) == "Box::new(x).y()"
    assert leading_path("a::b::C { x }") == ("a::b::C", " { x }")
    assert leading_path("|x| x") == ("", "|x| x")
