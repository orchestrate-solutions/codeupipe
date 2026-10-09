"""lexical: comment/literal blanking, bracket matching, frames."""

import pytest

from codeupipe_lint.anonymous_steps.lexical import (expression_end, frames, function_scope, line_col, line_starts,
                                          match_close, receiver_root, split_args, strip_source)


def _kept_same_shape(src, out):
    assert len(out) == len(src)
    assert [i for i, c in enumerate(src) if c == "\n"] == [i for i, c in enumerate(out) if c == "\n"]


@pytest.mark.parametrize("lang,src,gone,kept", [
    ("rust", "a // |x| x\nb", "|x|", "a"),
    ("rust", "/* outer /* inner */ |x| */ c", "|x|", "c"),
    ("rust", 'let s = r#"has "quotes" |x|"#; d', "|x|", "d"),
    ("rust", "fn f<'a>(x: &'a str) -> char { '|' }", "|", "'a"),
    ("cpp", '#define F(x) [](int){ return x; }\nint y;', "[]", "int y"),
    ("cpp", 'auto s = R"xy(a [](){} b)xy"; int z;', "[]", "int z"),
    ("cpp", "int big = 1'000'000; auto c = '[';", "[", "1'000'000"),
    ("kotlin", 'val s = """ Filter { it } """\nval t = 1', "Filter", "val t"),
    ("csharp", 'var s = @"a ""x => y"" b"; var t = 1;', "=>", "var t"),
    ("csharp", 'var s = $"{a => b}"; var t = 1;', "=>", "var t"),
])
def test_strip_blanks_comments_and_literals(lang, src, gone, kept):
    out = strip_source(src, lang)
    _kept_same_shape(src, out)
    assert gone not in out
    assert kept in out


def test_match_close_and_split_args():
    text = "f(a, g(b, c), [d, e], { f, g }, h)"
    close = match_close(text, 1)
    assert close == len(text) - 1
    assert [text[s:e] for s, e in split_args(text, 1, close)] == ["a", "g(b, c)", "[d, e]", "{ f, g }", "h"]


def test_line_col_is_one_based():
    starts = line_starts("ab\ncd\n")
    assert line_col(starts, 0) == (1, 1)
    assert line_col(starts, 4) == (2, 2)


def test_frames_and_function_scope():
    text = "struct S { fn m() { if x { y } } }\nfn f() { struct L { } }"

    def kind_of(head, parent_kind):
        if head.startswith("fn") or "fn " in head:
            return "code"
        if head.startswith("struct"):
            return "type"
        return "other"

    fr = frames(text, kind_of)
    assert [(f.kind, f.head) for f in fr] == [("type", "struct S"), ("code", "fn m()"), ("code", "if x"),
                                             ("code", "fn f()"), ("type", "struct L")]
    assert function_scope(fr, text.index("y")) == 1
    assert function_scope(fr, text.index("L")) == 3
    assert function_scope(fr, text.index("S")) is None


def test_expression_end():
    text = "let x = f(a; b) + 1; next"
    assert text[:expression_end(text, 8)] == "let x = f(a; b) + 1"
    kt = "val x = foo\n    .bar { it }\nval y = 2"
    assert kt[8:expression_end(kt, 8, newline_ends=True)] == "foo\n    .bar { it }"


def test_receiver_root_walks_back_a_method_chain():
    text = "p.add_parallel(Parallel::new().with(A).with(B(1)))"
    assert receiver_root(text, text.rindex(".with")) == "Parallel::new"
    text = "String::with_capacity(4).len()"
    assert receiver_root(text, text.index(".len")) == "String::with_capacity"
