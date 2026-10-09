# codeupipe-lint

Two linters for codeupipe pipelines: anonymous steps (seven languages) and
invariants (Python). Standard library only; depends on `codeupipe`.

## Anonymous-step linter

Step identity (conformance/API.md, "Step identity") makes a step's identity a
pointer to its filter. Anonymous steps have no such pointer and are
unsupported. The runtimes refuse what they can detect; this linter flags all
of them at authoring time, and for some cases it is the **only** check: a
struct or class defined inside a function looks like an ordinary type at
runtime in Go, Rust and C++, and C++ free functions have no derivable name.

```bash
python -m codeupipe_lint.anonymous_steps <paths...>            # files or directories
python -m codeupipe_lint.anonymous_steps --lang go --lang rust runtimes conformance
python -m codeupipe_lint.anonymous_steps --exclude '*/tests/lint/fixtures/*' .
python -m codeupipe_lint.anonymous_steps --rules               # list the rule ids
```

Each finding is one line, and the message names the fix:

```
path:line:col  CUP-A001 lambda-step  Valve predicate is a lambda. Define it at module level (...) so it has a stable identity and can be tested on its own.
```

With no paths, both linters read them from `cup.config.json`
([docs/config.md](../../docs/config.md)).

Exit code: **0** no anonymous steps, **1** anonymous steps found, **2** an
analyzer could not run (a missing Go toolchain, JavaScript runtime or
TypeScript compiler). A check that could not run is never reported as clean.

From Python: `codeupipe_lint.anonymous_steps.lint_pipeline.lint_paths(paths, languages=None, exclude=None)`
returns the result Payload (`findings`, `suppressed`, `errors`, `report`, `exit_code`).

## Rules

| id | slug | what |
|---|---|---|
| CUP-A000 | parse-error | the file could not be parsed or read (Python, Go, TypeScript) |
| CUP-A001 | lambda-step | a lambda, closure, arrow function, func literal, function expression, anonymous function or anonymous method; or the result of a same-file function that returns one |
| CUP-A002 | local-function-step | a named function declared inside a function (Python nested `def`, TS nested `function`, Rust nested `fn`, Kotlin local `fun`, C# local function or top-level-statement function) |
| CUP-A003 | local-type-step | a class, struct, enum or union declared inside a function, or an instance/value of one |
| CUP-A004 | anonymous-type-step | an anonymous type: TS object literal or class expression, Go anonymous struct literal, Kotlin `object :` expression, C# `new { .. }` |
| CUP-A005 | unnamed-pipeline-step | a plain, unnamed `Pipeline` nested as a step; nested pipelines must be named Pipeline types |
| CUP-A006 | entry-script-step | Python: a class or function of a script (`__main__`), added from its `if __name__ == "__main__":` block |
| CUP-A007 | free-function-step | C++: a free function as a filter or predicate; C++ filters must be types |
| CUP-A008 | function-predicate | Python, TypeScript: a named function as a Valve predicate. Predicates are objects with `test(payload)` (conformance/API.md, "Valve"). In Go, Kotlin, C#, Rust and C++ a function is not a predicate type, so the compiler already refuses it |

A step is any argument of the add methods (`add_filter`, `add_tap`,
`add_pipeline`, `add_parallel` and each language's spelling, on any
receiver), and both arguments of a Valve (inner filter and predicate). The
name argument, while runtimes still take one, is ignored: the rules do not
depend on it. A Valve passed as a step is not itself a finding; its
arguments are checked where it is constructed. Anonymous values are followed
through simple local bindings (`x = lambda ..`, `let f = |..| ..`,
`auto p = [](..){..}`, `val f = Filter { .. }`, `pred := func(..) ..`) and
through same-file factories (a function whose return is anonymous, or whose
declared return type is a function type or a plain `Pipeline`).

## Suppression

A comment containing `cup: allow-anonymous` (`# cup: allow-anonymous` in
Python, `// cup: allow-anonymous` elsewhere; any text may follow) suppresses
a finding when it is on the finding's line, on the line of the enclosing add
or Valve call, or alone on the line directly above. Suppressed findings are
counted in the summary. Use it only where the anonymous step is the point,
as in the tests that exercise the runtimes' refusal
(`tests/core/test_step_identity.py`, `runtimes/ts/tests/step_identity.test.ts`).

## How each language is checked, and the limits

The Python side is stdlib-only. Where a language's own parser is available on
the machine it is used; otherwise a lexical scan.

| language | method | runtime also refuses |
|---|---|---|
| Python | stdlib `ast` | everything |
| Go | `go/parser` + `go/ast`, a stdlib Go helper (`go/main.go`) built once into a cache (`CUP_LINT_CACHE`, default under the temp dir) | func literals; **not** local types |
| TypeScript | the TypeScript compiler API (parser + checker) in `ts/anonymous_steps.mjs`, run with bun or node | everything, with the build step |
| Rust | lexical scan | closures; **not** local types |
| C++ | lexical scan | lambdas; **not** local types or free functions |
| Kotlin | lexical scan | everything |
| C# | lexical scan | everything |

**Python.** Names resolve lexically (innermost function scope out to the
module; a parameter, loop target or import shadows). A name bound two
different ways in one scope is not flagged. CUP-A006 is deliberately
conservative: only a module with a `__main__` guard, only steps added from
that block or from a module-level function it calls (transitively); a
script without a guard is not flagged (the runtime still refuses it).
Not seen: `functools.partial`,
`type(...)`-built classes, steps built in another module (all refused at
runtime).

**Go.** Bindings are per function, flattened across blocks. A call with one
func-literal argument (`FilterFunc(func(..) ..)`) counts as a converted
func literal. Factories count through `f, err := factory()` (the first
result). Not seen: a func literal stored in a struct field of a named type
(`Adapter{fn: func..}`): the step is the named `Adapter`, and neither the
runtime nor the linter sees the closure inside.

**TypeScript.** Only `const` bindings are followed (a `let` may be
reassigned). Calls on a `TypedPipeline` (the typed variant, which still
takes names) are out of scope. The compiler comes from
`CUP_LINT_TYPESCRIPT` (a `typescript` package directory) or
`runtimes/ts/node_modules/typescript` (`npm ci` in runtimes/ts).

**Rust, C++, Kotlin, C#: lexical scan** (`lexical.py`, `lexical_engine.py`).
Comments, string/char literals (raw strings, C++ digit separators, Rust
lifetimes, C# verbatim/interpolated, Kotlin raw strings) and C++
preprocessor lines are blanked, blocks are paired and classified as
function bodies or type bodies from the text before their `{`, and each
argument is classified by pattern. Known limits, each pinned by a
`known_limits` fixture under `tests/lint/fixtures/<lang>/`:

- Scopes are flattened per function body: a local type in one block
  shadows a same-named outer type for the whole function (false positive).
- Only this file is seen: a factory, free function or closure defined in
  another file or a header is not followed (false negative).
- Macros are opaque (Rust `pred!()`, C++ macros are blanked).
- C++ and C#: a lambda *anywhere* in a step argument counts, including a
  lambda passed to a named filter's constructor
  (`std::make_unique<Configured>([](..){..})`, `new Options(x => ..)`,
  false positive). Conversely a C# local function wrapped in an adapter
  class (`new FuncFilter(LocalStep)`) is not seen.
- C++: free functions are those *defined* at namespace scope in this file,
  plus any `&ns::name` address-of; a function only declared in a header is
  not known. Brace-initialised Valves (`Valve{..}`) are not recognised.
- Kotlin: `Name { .. }` reads as a SAM lambda, so a named class whose
  constructor takes a lambda, called with only a trailing lambda, is a
  false positive; lambdas passed through scope functions (`run { .. }`)
  are not seen.
- Generic arguments containing commas (`Foo<A, B>`) can split an argument
  list in the wrong place.

## Layout

The linter is a CUP pipeline (dogfooding), built with this repo's own
`codeupipe` core from module-level filters, one class per file:

```
CollectFiles -> AnalyzePython -> AnalyzeGo -> AnalyzeTypescript -> AnalyzeRust
  -> AnalyzeCpp -> AnalyzeKotlin -> AnalyzeCsharp -> ApplySuppressions -> FormatReport
```

Tests mirror the source under `tests/lint/anonymous_steps/`; fixtures, each
marking its expected findings with `expect: CUP-A00N` comments, are under
`tests/lint/fixtures/<lang>/`.

# Invariant linter (Python)

The runtime cannot enforce every rule a pipeline depends on. This linter
checks the ones that are visible in the source. Python only for now.

```bash
python -m codeupipe_lint.invariants <paths...>
python -m codeupipe_lint.invariants --exclude '*/fixtures/*' .
python -m codeupipe_lint.invariants --rules
```

Same output and exit codes as the anonymous-step linter: one line per finding
with a message that names the fix; **0** clean, **1** violations found, **2**
a path could not be read. From Python:
`codeupipe_lint.invariants.lint_pipeline.lint_paths(paths, exclude=None)`.

| id | slug | what |
|---|---|---|
| CUP-I000 | parse-error | the file could not be parsed |
| CUP-I001 | payload-internals | a write through a Payload's `_data` (`payload._data[k] = v`, `payload._data.update(..)`, `del payload._data[k]`) |
| CUP-I002 | shared-value-mutation | an in-place change to a value that came from `payload.get(..)`: `payload.get("items").append(x)`, or the same through a local name, a nested key, or the loop variable of a `for` over it |
| CUP-I003 | state-read-in-step | a Filter (`call`) or Valve predicate (`test`) reaching pipeline State: `self.pipeline.state.executed`, `PIPELINE.state.errors`, or an attribute `__init__` set to a State |

**Why CUP-I002.** A Payload owns its keys, not its values.
`payload.get("items")` returns the live list, shared with every copy of the
Payload and with the caller's input, so appending to it changes all of them.
The conformance suite requires that this never happens
(`payload/nested-input-is-never-mutated`) and the runtime has no way to
refuse it. The fix is to copy, change the copy, and insert it.

**A write through the API is not flagged.** `insert`, `remove` and `merge`
change the Payload in place by design. These rules are about changes behind
the API.

**Why CUP-I003.** A Filter's result and a Valve's decision must depend only
on the Payload. A step is never handed State, so the only way to read it is
to hold a pipeline or a State, and that makes the step's behaviour depend on
what ran before it, which the static export cannot reproduce. Taps and Hooks
are observers, so `observe` and Hook methods are not checked.

`self.state` is not flagged when it is the step's own attribute. `<x>.state`
is flagged when what follows is one of State's own members, or when the name
it hangs off says it is a pipeline. A pipeline held under a name that does
not contain "pipeline", read only through a member that is not State's own, is a known miss.

CUP-I001 and CUP-I002 are checked in methods named `call`, `observe` or `test` of any class; the payload
is the method's first parameter after `self`, and any name assigned from
`payload.insert(..)`, `.remove(..)`, `.merge(..)`.

Known limits:

- `name += [..]` on a local name is not flagged: that form is almost always a
  number or a string, and a list there would be a miss.
- A value passed to a helper function and changed there is not followed.
- `payload.to_dict()` is a top-level copy whose nested values are still
  shared; changes to those are not flagged.
- A name rebound in one branch is treated as rebound from then on.

Suppress an intentional one with a `cup: allow-mutation` or
`cup: allow-state-read` comment on the line or alone on the line above.
