"""The shared scan behind the lexical analyzers (Rust, C++, Kotlin, C#).

Each language supplies a *spec* (a SimpleNamespace of hooks, built in its
``analyze_<lang>.py``):

- ``lang``: rules.py language key.
- ``kind_of(head, parent_kind)``: frame kind for a ``{`` (lexical.frames).
- ``function_info(head)``: ``(name, return_text)`` when a code frame's head
  declares a named function, else None. Functions inside a type body count
  only when ``methods_are_functions`` (C#, Kotlin).
- ``expression_function_re`` (optional): groups ``ret``, ``name``; a
  brace-less function whose body is the expression after the match.
- ``local_type_re``: group ``name``; a match inside a function body declares
  a local type.
- ``local_function_re`` (optional): group ``name``; a match inside a
  function body declares a local function.
- ``binding_re``: a regex (or list) with group ``name``; the bound
  expression runs from the match end to the end of the statement.
- ``newline_ends``: whether a newline ends a statement (Kotlin): a binding's
  expression, and a block's head.
- ``calls``: ``[(regex ending in "(", role_of(index, count), expands[, accept])]``;
  ``expands`` = argument elements are steps (``add_parallel``); the optional
  ``accept(stripped, match_start)`` can reject a match (by its receiver).
- ``elements(text)``: spans of the elements of a collection literal, or None.
- ``trailing_lambda``: a ``{`` right after the call's ``)`` is one more
  argument (Kotlin).
- ``named_arg_re`` / ``named_roles`` (optional): a named argument
  (``predicate = ..`` in Kotlin, ``predicate: ..`` in C#) is classified
  without its name, and its role taken from ``named_roles`` when listed.
- ``classify(text, ctx)``: ``(rule, subject, noun)`` or None, where
  ``ctx`` offers ``local_type(name)``, ``local_function(name)``,
  ``binding(name)``, ``is_bound(name)``, ``function(name)``, ``function_ctx(name)``,
  ``body(name)`` and ``classify(text)``.

Scopes are function bodies (the outermost code frame), flattened across
nested blocks; bindings outside any function are file-level.
"""

import re
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

from .finding import Finding
from .lexical import (enclosing, expression_end, frames, function_scope, line_col, line_starts, match_close,
                      split_args, strip_source)
from .rules import UNNAMED_PIPELINE, make_finding

_LAMBDA_RULE = "CUP-A001"


def scan(path: str, text: str, spec: SimpleNamespace) -> List[Finding]:
    stripped = strip_source(text, spec.lang)
    all_frames = frames(stripped, spec.kind_of, getattr(spec, "newline_ends", False))
    starts = line_starts(stripped)

    # Named functions: code frames whose parent is not code.
    functions: Dict[str, dict] = {}
    labels: Dict[Optional[int], str] = {None: "the file"}
    for index, frame in enumerate(all_frames):
        parent_kind = all_frames[frame.parent].kind if frame.parent is not None else "file"
        if frame.kind != "code" or parent_kind == "code":
            continue
        info = spec.function_info(frame.head)
        labels[index] = ("%s()" % info[0]) if info else "a function"
        if info and (parent_kind != "type" or getattr(spec, "methods_are_functions", False)):
            functions.setdefault(info[0], {"name": info[0], "ret": info[1], "frame": index, "span": None,
                                           "parent_kind": parent_kind, "head": frame.head})

    def enclosing_kind(offset: int) -> str:
        inside = enclosing(all_frames, offset)
        return all_frames[inside[-1]].kind if inside else "file"

    # Expression-bodied functions (no braces), e.g. C# `T Name(..) => expr;`.
    if getattr(spec, "expression_function_re", None) is not None:
        for m in spec.expression_function_re.finditer(stripped):
            kind = enclosing_kind(m.start())
            if kind == "code":
                continue  # a local function; local_function_re covers it
            end = expression_end(stripped, m.end(), getattr(spec, "newline_ends", False))
            functions.setdefault(m.group("name"), {"name": m.group("name"), "ret": m.group("ret"), "frame": None,
                                                   "span": (m.end(), end), "parent_kind": kind,
                                                   "at": m.start(), "head": m.group(0)})

    def scope_of(offset: int) -> Optional[int]:
        return function_scope(all_frames, offset)

    local_types: Dict[Optional[int], Dict[str, str]] = {}
    for m in spec.local_type_re.finditer(stripped):
        scope = scope_of(m.start("name"))
        if scope is not None:
            local_types.setdefault(scope, {})[m.group("name")] = labels[scope]
    local_functions: Dict[Optional[int], Dict[str, str]] = {}
    if getattr(spec, "local_function_re", None) is not None:
        for m in spec.local_function_re.finditer(stripped):
            scope = scope_of(m.start("name"))
            if scope is not None:
                local_functions.setdefault(scope, {})[m.group("name")] = labels[scope]
    bindings: Dict[Optional[int], Dict[str, List[Tuple[int, int]]]] = {}
    binding_res = spec.binding_re if isinstance(spec.binding_re, (list, tuple)) else [spec.binding_re]
    for binding_re in binding_res:
        for m in binding_re.finditer(stripped):
            start = m.end()
            end = expression_end(stripped, start, getattr(spec, "newline_ends", False))
            bindings.setdefault(scope_of(m.start()), {}).setdefault(m.group("name"), []).append((start, end))

    def make_ctx(scope: Optional[int], visiting: frozenset) -> SimpleNamespace:
        def local_type(name):
            return local_types.get(scope, {}).get(name)

        def local_function(name):
            return local_functions.get(scope, {}).get(name)

        def binding(name):
            for where in (scope, None):
                spans = bindings.get(where, {}).get(name)
                if spans:
                    key = (where, name)
                    if key in visiting:
                        return None
                    inner = make_ctx(where, visiting | {key})
                    got = [inner.classify(stripped[s:e]) for s, e in spans]
                    if got[0] is None or any(g is None or g[0] != got[0][0] for g in got):
                        return None
                    rule, subject, noun = got[0]
                    return rule, (("`%s`, %s" % (subject, noun)) if subject else noun)
            return None

        def is_bound(name):
            return any(bindings.get(where, {}).get(name) for where in (scope, None))

        def function(name):
            return functions.get(name)

        def function_ctx(name):
            info = functions.get(name)
            if info is None or ("fn", name) in visiting:
                return None
            where = info["frame"] if info["frame"] is not None else scope_of(info["at"])
            return make_ctx(where, visiting | {("fn", name)})

        def body(name):
            info = functions.get(name)
            if info is None:
                return ""
            if info["span"] is not None:
                return stripped[info["span"][0]:info["span"][1]]
            frame = all_frames[info["frame"]]
            return stripped[frame.open + 1:frame.close]

        ctx = SimpleNamespace(local_type=local_type, local_function=local_function, binding=binding, is_bound=is_bound,
                              function=function, function_ctx=function_ctx, body=body)
        def classify(t):
            return spec.classify(t.strip(), ctx)

        ctx.classify = classify
        return ctx

    findings: List[Finding] = []
    seen = set()

    def report(start: int, end: int, role: str, call_start: int) -> None:
        text_arg = stripped[start:end]
        got = make_ctx(scope_of(start), frozenset()).classify(text_arg)
        if got is None:
            return
        rule, subject, noun = got
        if rule == UNNAMED_PIPELINE and role == "Valve predicate":
            return
        if (start, rule) in seen:
            return
        seen.add((start, rule))
        line, col = line_col(starts, start)
        what = ("`%s` is %s" % (subject, noun)) if subject else ("is " + noun)
        findings.append(make_finding(spec.lang, path, line, col, rule, role, what, line_col(starts, call_start)[0]))

    for call in spec.calls:
        pattern, role_of, expands = call[:3]
        accept = call[3] if len(call) > 3 else None
        for m in pattern.finditer(stripped):
            if accept is not None and not accept(stripped, m.start()):
                continue
            open_index = m.end() - 1
            call_start = m.start()
            if stripped[open_index] == "{":  # Kotlin: addFilter { ... }
                report(open_index, match_close(stripped, open_index) + 1, role_of(0, 1), call_start)
                continue
            close = match_close(stripped, open_index)
            args = split_args(stripped, open_index, close)
            count = len(args)
            trailing = None
            if getattr(spec, "trailing_lambda", False):
                k = close + 1
                while k < len(stripped) and stripped[k] in " \t":
                    k += 1
                if k < len(stripped) and stripped[k] == "{":
                    trailing = (k, match_close(stripped, k) + 1)
                    count += 1
            for index, (s, e) in enumerate(args):
                role = role_of(index, count)
                named = spec.named_arg_re.match(stripped, s, e) if getattr(spec, "named_arg_re", None) else None
                if named:
                    role = spec.named_roles.get(named.group(1), role)
                    s = named.end()
                elements = spec.elements(stripped[s:e]) if expands else None
                if elements is not None:
                    for es, ee in elements:
                        report(s + es, s + ee, role, call_start)
                else:
                    report(s, e, role, call_start)
            if trailing is not None:
                report(trailing[0], trailing[1], role_of(count - 1, count), call_start)
    return findings


def unwrap_calls(text: str, wrappers: "re.Pattern") -> str:
    """Strip wrappers like ``Box::new(...)`` / ``std::make_unique<T>(...)`` whose
    parentheses span the whole text; repeat."""
    text = text.strip()
    while True:
        m = wrappers.match(text)
        if not m:
            return text
        open_index = m.end() - 1
        close = match_close(text, open_index)
        if close != len(text) - 1:
            return text
        text = text[open_index + 1:close].strip()


def leading_path(text: str) -> Tuple[str, str]:
    """``(path, rest)`` for text starting with an identifier path (``a::b::C``, ``a.b.C``)."""
    m = re.match(r"((?:[A-Za-z_]\w*)(?:\s*(?:::|\.)\s*[A-Za-z_]\w*)*)", text)
    if not m:
        return "", text
    return m.group(1), text[m.end():]
