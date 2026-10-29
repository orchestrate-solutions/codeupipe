# Conformance suite

The rules are in **[API.md](API.md)**, the CUP API contract. This suite
checks them.

**[ADD.md](ADD.md)** is the contract of `codeupipe add`, the command that
adds components to a project, with its cases in [add/](add/) and its own
judge, `python conformance/add.py`.

One set of language-neutral cases, a runner, and **one judge** (`run.py`).
The judge is itself a codeupipe pipeline, in [judging/](judging/): one step
reads the cases, one runs each target, one compares, and one writes the
matrix. Each step is tested alone in `tests/conformance/test_judge_pipeline.py`.

The Python runner is built the same way, in
[runners/python/case_runner/](runners/python/case_runner/): one pipeline plays
a case and one times a scenario. Its steps are tested alone in
`tests/conformance/test_case_runner.py`.
The dynamic run and each compiled form are held to exactly the same
comparison.

```bash
python conformance/run.py                       # every target
python conformance/run.py python:run python:static-inline
```

Results: `results/latest.md` (matrix) and `results/latest.json` (details).
The committed snapshot is [MATRIX.md](MATRIX.md).

**Benchmarks** run on the same runner: `python conformance/bench.py`
([BENCH.md](BENCH.md)). The runner has a `bench` mode that times the
scenarios in `bench/scenarios.json`.

**Speed is measured, not judged.** CI runs `bench.py` and keeps the numbers
(the job summary and an artifact), and never fails because of them: a shared
machine is too noisy for a speed gate. A comparison with a recorded baseline
(`bench/baseline.json`) is kept for a machine whose resources are fixed, such
as a constrained container. No test and no CI job runs it:

```bash
python conformance/bench.py --check                  # outside ±25% of the baseline
python conformance/bench.py --check --tolerance 15
python conformance/bench.py --record                 # record the baseline
python conformance/bench.py rust:run --record        # only the Rust numbers
```

A number is kept as a ratio to a reference workload (plain dict writes
behind function calls) that the runner times beside it, so the check does
not depend on how fast the machine is. Slower than the band is a regression.
Faster than the band also fails, with the instruction to record again:
otherwise the next regression would hide inside the gain. There is one
baseline for each Python version, and one each for the Rust and Go runs,
which do not depend on Python (each of those runners times a reference of map
writes of its own).
`--record` with targets named replaces only those targets. Run it on a quiet machine: under heavy
load a number can leave the band.

| Target | How it runs (all offline) |
|---|---|
| `python:run`, `python:run_async` | `codeupipe.core` Pipeline, sync and async entry points |
| `python:static-steps`, `python:static-inline` | `codeupipe.compile` fast mode, loaded from disk (no State or Hooks: ✅\*) |
| `python:static-observe` | `codeupipe.compile` with `observe=True`: State and Hooks judged too |
| `typescript:run` | `packages/codeupipe-ts` Pipeline. Node runs the `.ts` runner as it is (Node 22.18 or later). With no arguments, `run.py` leaves this target out when the machine has no such Node |
| `typescript:static` | `packages/codeupipe-compile-ts`: the pipeline as plain code, written to a file and imported (no State or Hooks: ✅\*). Needs `npm ci` in that package and a built core package; `run.py` leaves it out when they are not there |
| `rust:run` | `packages/codeupipe-rs` Pipeline. `cargo run --release --offline` builds the runner, which has no dependency to download. With no arguments, `run.py` leaves this target out when the machine has no `cargo` |
| `go:run` | `packages/codeupipe-go` Pipeline. `go run` builds the runner with `GOPROXY=off`: its `go.mod` points at the package with a `replace`, and it reads JSON with `encoding/json`, so it has nothing to download. With no arguments, `run.py` leaves this target out when the machine has no `go` |

## Statuses

| | meaning |
|---|---|
| ✅ | every expectation matched |
| ✅* | everything the target *can observe* matched. Static code has no State or Hooks, so those checks cannot run |
| ❌ | something observable differed |
| ➖ | the target cannot express the case (e.g. the compiler refuses a nested pipeline). Never counted as a pass |

## Case format (`cases/*.json`)

```json
{"id": "tap/failure-never-halts-the-pipeline",
 "hooks": false,
 "steps": [
   {"kind": "filter", "name": "s1", "op": "set", "key": "a", "value": 1},
   {"kind": "tap", "name": "audit", "op": "fail", "message": "sink down"},
   {"kind": "valve", "name": "g", "when": {"op": "truthy", "key": "flag"},
    "filter": {"op": "set", "key": "b", "value": 2}},
   {"kind": "pipeline", "name": "inner", "steps": [ ... ]}],
 "input": {},
 "expect": {"output": {...}  |  "error": {"message_contains": "..."},
            "state": {"executed": [...], "skipped": [...], "errors": [...]},
            "taps": [...], "hooks": ["before:", "before:s1", ...]}}
```

Three more keys are for the cases about State and runs that overlap:

- `"given_state": true` in a case: the runner gives the run a new State
  (`run(p, state)`), and reports that State as `state`.
- `expect.inner_states`: the State of each run that a `run_again` step
  started, in order.
- `expect.pipeline_state`: `state` on the Pipeline after the run ends. A
  compiled form is a function and has no Pipeline object, so it cannot
  show this.

Every case also checks, implicitly, that **the caller's input was not mutated**.
Numbers compare as JSON numbers (`1 == 1.0`), but `true` is never `1`.

### Reference vocabulary (a runner implements these natively)

| kind | op | behaviour |
|---|---|---|
| filter | `set` key, value | insert `key = value` |
| filter | `copy` from, to | insert `to = get(from)` (null if missing) |
| filter | `add` key, by | insert `key = get(key, 0) + by` |
| filter | `append` key, value | insert `key = copy(get(key) or []) + [value]` |
| filter | `fail` message | raise an error carrying `message` |
| filter | `remove` key | `remove(key)` |
| filter | `merge` value | `merge(Payload(value))` |
| filter | `has` key, to | insert `to = has(key)` |
| filter | `mutate` key, value | `insert(key, value)` as a statement of its own, then return the payload |
| filter | `run_again` input | when `get("inner")` is not true: run the pipeline that this step is in one more time, with `input` and a new State, and keep that State for the report. Then return the payload with no change. This is a second run that starts and ends while the first one is in progress. How a pipeline is run again depends on the target (a method of the Pipeline, or for a compiled form a second call of its function), so the runner gives the step that as a function |
| tap | `record` key | append `get(key)` to the runner's tap log |
| tap | `fail` message | raise |
| valve `when` | `equals` key, value | `get(key) == value` |
| valve `when` | `truthy` key | `get(key)` is truthy (missing ⇒ false) |
| hooks | `"hooks": true` | record `before:<step>`, `after:<step>`, `error:<step>`; pipeline-level events use an empty step name. On a filter failure: `error:<step>` then `error:`. The runner maps each reported step label (API.md) back to the case's step name |

## Runner protocol

`runner <target> < cases.json > results.json`. For each case the runner
emits `{"id", "output" | "error", "state"?, "taps", "hooks"?, "input_after"}`,
or `{"id", "unsupported": reason}`. Runners **never judge**.

Adding a runtime: implement the vocabulary, build pipelines from `steps`,
emit that shape, and register the command in `run.py`'s `TARGETS`. A runner
must not download anything.

## Reference behaviour and open questions

Expectations follow the [API contract](API.md) where it is explicit (Plane B: a Tap failure
never halts the pipeline). Where it is silent, they encode Python
`codeupipe.core`'s behaviour. These are the ones to settle deliberately:

1. **`on_error` fires at both levels.** On a filter failure it fires for
   the failing step, then for the pipeline (`… before:b, error:b, error:`),
   mirroring `before`/`after`; the error replaces the two `after` events
   that never happen. A retry needs the step, and a pipeline-level handler
   must still see every failed run. Tap failures fire neither (Plane B).
2. **Hooks around a skipped Valve.** Python fires `before:v` / `after:v` even
   when the Valve skips its filter.
3. **`equals` across types.** Python's `==` makes `1 == true`; JSON does not.
   TypeScript uses `===`, which does not compare lists or maps by content.
   Rust and Go compare by content, and a number is never equal to a
   boolean. No case depends on it yet.
4. **`truthy` across languages.** An empty list or map is false in Python
   and true in JavaScript. Each runner uses the rule of its language; Rust
   and Go have no rule of their own and follow Python. No case depends on it
   yet.
