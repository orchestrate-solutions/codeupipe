# codeupipe-lint

Two linters for codeupipe pipelines, in Python: anonymous steps, and
invariants. Standard library only; depends on `codeupipe`.

## Using a part of the rules

Each rule can be switched off. There are three ways.

| For | How |
|---|---|
| One line | A comment on the line: `# cup: allow-anonymous`, `# cup: allow-mutation`, `# cup: allow-state-read`, `# cup: allow-outside-write`, `# cup: allow-shared-file` |
| Some files | `--exclude GLOB`, or `lint.exclude` in `cup.config.json` |
| The whole project | `--disable RULE`, or `lint.disable` in `cup.config.json` |

```bash
python -m codeupipe_lint.invariants --disable CUP-I005 src
```

A rule id that does not exist is an error. A rule of the other linter can be
in the list: each linter uses the ids that are its own.

## Anonymous-step linter

Step identity (conformance/API.md, "Step identity") makes a step's identity a
pointer to its filter. Anonymous steps have no such pointer and are
unsupported. The runtime refuses them when the step is added; this linter
flags them at authoring time.

```bash
python -m codeupipe_lint.anonymous_steps <paths...>            # files or directories
python -m codeupipe_lint.anonymous_steps --exclude '*/tests/lint/fixtures/*' .
python -m codeupipe_lint.anonymous_steps --rules               # list the rule ids
```

Each finding is one line, and the message names the fix:

```
path:line:col  CUP-A001 lambda-step  Valve predicate is a lambda. Define it at module level (...) so it has a stable identity and can be tested on its own.
```

With no paths, both linters read them from `cup.config.json`
([docs/config.md](../../docs/config.md)).

Exit code: **0** no anonymous steps, **1** anonymous steps found, **2** a
path could not be read.

From Python: `codeupipe_lint.anonymous_steps.lint_pipeline.lint_paths(paths, exclude=None)`
returns the result Payload (`findings`, `suppressed`, `errors`, `report`, `exit_code`).

### Rules

| id | slug | what |
|---|---|---|
| CUP-A000 | parse-error | the file could not be parsed or read |
| CUP-A001 | lambda-step | a lambda, or the result of a same-file function that returns one |
| CUP-A002 | local-function-step | a named function declared inside a function |
| CUP-A003 | local-type-step | a class declared inside a function, or an instance of one |
| CUP-A005 | unnamed-pipeline-step | a plain, unnamed `Pipeline` nested as a step; nested pipelines must be named Pipeline types |
| CUP-A006 | entry-script-step | a class or function of a script (`__main__`), added from its `if __name__ == "__main__":` block |
| CUP-A008 | function-predicate | a named function as a Valve predicate. Predicates are objects with `test(payload)` (conformance/API.md, "Valve") |

A step is any argument of `add_filter`, `add_tap` or `add_pipeline` (on any
receiver), and both arguments of a Valve (inner filter and predicate). A
Valve passed as a step is not itself a finding; its arguments are checked
where it is constructed. Anonymous values are followed through simple local
bindings (`x = lambda ..`) and through same-file factories (a function whose
return is anonymous, or a plain `Pipeline`).

### Suppression

A comment containing `# cup: allow-anonymous` (any text may follow)
suppresses a finding when it is on the finding's line, on the line of the
enclosing add or Valve call, or alone on the line directly above. Suppressed
findings are counted in the summary. Use it only where the anonymous step is
the point, as in the tests that exercise the runtime's refusal
(`tests/core/test_step_identity.py`).

### Limits

Names resolve lexically (innermost function scope out to the module; a
parameter, loop target or import shadows). A name bound two different ways
in one scope is not flagged. CUP-A006 is deliberately conservative: only a
module with a `__main__` guard, only steps added from that block or from a
module-level function it calls (transitively); a script without a guard is
not flagged (the runtime still refuses it). Not seen: `functools.partial`,
`type(...)`-built classes, steps built in another module (all refused at
runtime).

### Layout

The linter is a CUP pipeline (dogfooding), built with `codeupipe` from
module-level filters, one class per file:

```
CollectFiles -> AnalyzePython -> ApplySuppressions -> FormatReport
```

Tests mirror the source under `tests/lint/anonymous_steps/`; fixtures, each
marking its expected findings with `expect: CUP-A00N` comments, are under
`tests/lint/fixtures/python/`.

## Invariant linter

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
| CUP-I004 | write-outside-filter | a Tap (`observe`), a predicate (`test`) or a Hook (`before`, `after`, `on_error`) that calls `insert`, `remove`, `merge` or `with_trace` on its payload |
| CUP-I005 | one-primitive-per-file | a second Filter, Tap, Hook, predicate or named Pipeline class at module level in one file |

**Why CUP-I002.** A Payload owns its keys, not its values.
`payload.get("items")` returns the live list, shared with every copy of the
Payload and with the caller's input, so appending to it changes all of them.
The conformance suite requires that this never happens
(`payload/nested-input-is-never-mutated`) and the runtime has no way to
refuse it. The fix is to copy, change the copy, and insert it.

**A write through the API is not flagged.** `insert`, `remove` and `merge`
change the Payload in place by design. These rules are about changes behind
the API.

**Why CUP-I004.** Only a Filter writes to the Payload, so every change to
the data is a step you can see in the pipeline. This rule is the guard: the
runtime does not check, so a write from a Tap, a Hook or a predicate that
gets past the linter does happen. A write to `payload.copy()` belongs to the
Tap, Hook or predicate that made the copy, and is not flagged. Suppress with `cup: allow-outside-write`.

**Why CUP-I005.** A primitive alone in its file can be found by its name,
tested alone, and used again in another pipeline. The pipeline file is where
the parts come together. The first primitive in a file is accepted; each one
after it is reported. Plain classes and functions beside the primitive are
not reported. Test files (`test_*.py`, `conftest.py`, anything under a
`tests` directory) are not checked: a test often needs several small steps
side by side. Suppress with `cup: allow-shared-file`.

**Why CUP-I003.** A Filter's result and a Valve's decision must depend only
on the Payload. A step is never handed State, so the only way to read it is
to hold a pipeline or a State, and that makes the step's behaviour depend on
what ran before it, which the static export cannot reproduce. Taps and Hooks
only watch, so `observe` and Hook methods are not checked.

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

Suppress an intentional one with a `cup: allow-mutation`, `cup: allow-outside-write`,
`cup: allow-shared-file` or
`cup: allow-state-read` comment on the line or alone on the line above.
