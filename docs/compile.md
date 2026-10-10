# Compile: what it guarantees

`codeupipe.compile` turns a live `Pipeline` into plain Python with no framework
import. This page says what the compiler lowers, what it refuses, and what
the compiled code does not have.

**The rule: anything that compiles behaves the same as the dynamic `run`.
Anything that cannot is refused at compile time, with the step named.** A
shape that compiles "successfully" and then behaves differently is a bug.

There are two modes. Pick per pipeline:

| | fast (default) | observable (`observe=True`) |
|---|---|---|
| compiled entry point | `run(data)` | `run(data, state=None, hooks=None, timing=False, trace_id=None)` |
| output | same as dynamic | same as dynamic |
| State (executed, skipped, errors, timings) | no | yes, into the `state` dict |
| Hooks | refused | yes, same order as dynamic |
| layouts | `steps`, `inline` | `steps` only |
| conformance | 11 pass, 16 partial (State/Hooks unobservable) | **27 / 27 pass** |
| 10 filters, µs per run (dynamic: 4.92) | 0.84 steps, **0.58 inline** | 1.95 |
| 10 filters + a Hook (dynamic: 5.96) | refused | 3.03 |

```python
from codeupipe.compile import build_export_pipeline_v2

out = build_export_pipeline_v2(write=False).run(Payload({
    "pipeline": pipeline,
    "lowering": "steps",      # or "inline": one flat run(), ~2x faster again
}))
out.get("files")              # [{"path": ..., "content": ...}], exposing run(dict) -> dict
```

## From the command line

```bash
python -m codeupipe.compile app.pipelines:checkout --out build/checkout
python -m codeupipe.compile app.pipelines:checkout --out build/checkout --lowering inline
python -m codeupipe.compile app.pipelines:checkout --out build/checkout --observe
```

`module:name` is a `Pipeline`, a function that builds one, or a named
`Pipeline` type. The package is written under `DIR/src/steps/`, and each
file written is printed. A directory that is not empty is refused unless
`--overwrite` is given (which adds and replaces files but removes none, so
steps deleted from the pipeline leave their old modules behind).

With no `module:name`, every pipeline listed under `compile` in
`cup.config.json` is compiled ([config.md](config.md)).

Exit code: **0** compiled, **1** refused (the message names the step and the
fix), **2** the command could not run. Nothing is written on 1 or 2. Tests:
[tests/compile/test_cli.py](../tests/compile/test_cli.py).

## Step labels in compiled code

A step has a label, the name of its class (`Validate`, `Validate#2` from the
second use; conformance/API.md). A label is not an identifier, so compiled
code never uses it as a name: each step gets a generated module and
function, `step_01_validate`, `step_02_validate`, and the label appears only
as a string in State and in Hook calls. That also rules out
every collision between a step and a builtin, a module global or the
generated `run()` (scorecard findings F3–F8).

## What lowers

| Shape | Static form | Checked by |
|---|---|---|
| Filter (`call`) | a function `dict -> dict` | conformance, parity spike |
| Valve (predicate object: `test(self, payload)`) | `if step_NN_predicate(data): data = step(data)`, the predicate's literal settings compiled in as `_when_<attr>` constants | conformance, parity spike, `test_export_instance_config` |
| Tap (`observe`) | the call wrapped in `try/except Exception` (Plane B: never halts) | conformance, `test_export_pipeline` |
| Nested Pipeline (a named `Pipeline` type) | its steps flattened in place; reported as the one nesting step | conformance, `test_export_pipeline` |
| Literal instance settings (`self.key` holding a str, number, ...) | compiled in as constants | `test_export_instance_config` |
| Type hints on a step (`Payload[Reads] -> Payload[Writes]`, hinted locals) | erased: compiled code carries no hints and never imports their names | `test_export_typed_steps` |
| Payload ops `get insert remove merge has to_dict copy` | dict operations; a write is an in-place statement (`data[k] = v`) | `test_rewrite_payload_ops` |

Evidence: all 27 conformance cases on both layouts (`python:static-steps`,
`python:static-inline`), and the parity spike at 2400/2400 inputs.

## What is refused

`UnsupportedFilterShape` is raised at compile time, naming the step. Tests:
[tests/compile/test_export_refusals.py](../tests/compile/test_export_refusals.py)
and the older shape tests beside it.

| Shape | Why there is no static form | What to do |
|---|---|---|
| **Hooks**, in the fast mode | the fast code has no lifecycle to hook into | compile with `observe=True`, or remove them |
| **Hooks on a nested pipeline**, in either mode | they belong to the inner run, which is flattened away | move them to the top-level pipeline |
| `observe=True` with `lowering="inline"` (`ValueError`) | inline writes the payload in place, so a Hook holding it would see later steps' writes | use the default `steps` layout |
| **Async steps** (async `call`/`observe`, Valve around one, async `test`) | static `run` is sync, as the dynamic `run` is: it raises `AsyncStepInSyncRun` on the same pipeline | make the step sync |
| **`payload.trace_id`, `payload.lineage`, `payload.with_trace`** | a plain dict carries neither | keep the step dynamic |
| any other payload attribute (`payload._data`, ...) | same: only the operations above have a dict form | use an compilable operation |
| callables or objects on `self` (filter or predicate), steps writing `self.x` | no source or literal to compile in | literal settings (predicates and filters are module-level classes anyway: the runtime refuses anything else) |

## What the fast mode gives up

The fast mode produces the same **output**. It does not produce:

- **State**: no executed / skipped / errors / timings.
- **Hook calls** (refused, above).
- **Tap errors**: contained, as in the dynamic runtime, but not recorded.
- **Nested pipeline names**: flattened away.

So conformance can judge the fast targets only on output, Taps and an
unchanged caller input: they pass the State and Hook cases as ✅\* (partial).

## Observable mode (`observe=True`)

```python
out = build_export_pipeline_v2(write=False).run(Payload({"pipeline": pipeline, "observe": True}))
# ... write out.get("files"), then:
state = {}
result = run(data, state=state, hooks=[AuditHook()], timing=True, trace_id="req-42")
state["executed"], state["skipped"], state["errors"], state["timings"], state["trace_id"]
```

It reproduces the dynamic run's observable behaviour exactly, and the
`python:static-observe` conformance target checks it on all 27 cases:

- **State** is written into the `state` dict you pass (reset each run):
  `executed`, `skipped`, `errors` as `(name, error)`, `timings` (only with
  `timing=True`), and `trace_id` as passed. Omit `state` if you only want
  Hooks.
- **Hooks** are called `before(step, data)`, `after(step, data)`,
  `on_error(step, error, data)`, with `step=None` for the pipeline, in the
  contract's order (conformance/API.md). They receive the **dict**, not a
  `Payload`: `.get` works, but treat it as read-only, and `trace_id` is on
  `state`, not on the data.
- **Hooks are passed at run time**, since the compiled code imports no
  framework and cannot rebuild hook objects. If the source pipeline had
  Hooks, the module lists them in `SOURCE_HOOKS` and `run()` **raises
  `TypeError` if `hooks` is omitted**, so they cannot be lost silently.
  Pass `hooks=()` to run without them on purpose.
- **Nested pipelines** run inline but report as the one step that nested
  them, in State and in Hooks, as dynamically. Their inner skips and Tap
  errors belong to the inner run and do not appear.
- **Tap failures** are recorded in `errors` and never reach `on_error`.
- Not carried: **lineage** (use `executed`), event listeners and contracts
  (refused, above).

Cost: 10 filters run in 1.95 µs against 0.84 for the fast per-step layout
and 4.92 for the dynamic run: about 2.5× faster than dynamic with the same
State and Hooks. With a Hook attached, 3.03 µs against 5.96.

## Testing compiled code

- **Fast mode:** the package is `run(dict) -> dict`, so test by output.
  The scorecard (`python -m scorecard.differential`) runs the dynamic and
  static forms on the same inputs and compares outputs, raised errors and
  input mutation.
- **Observable mode:** assert on the `state` dict and on a recording Hook,
  exactly as you would on `pipeline.state` and a Hook in the dynamic
  runtime. `tests/compile/test_export_observe.py` runs both forms side by side
  and asserts they match.
- `run_filter` and `assert_state` from `codeupipe.testing` target the
  dynamic runtime only.
