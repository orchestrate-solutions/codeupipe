# Conformance suite

The rules every runtime is held to are in **[API.md](API.md)**, the CUP API
contract. This suite checks them.

One set of language-neutral cases, one small runner per runtime, and **one
judge** (`run.py`). Every runtime, and both of Python's static lowerings, is
held to exactly the same comparison.

```bash
python conformance/run.py                       # every available target
python conformance/run.py python:run go:run
```

Results: `results/latest.md` (matrix) and `results/latest.json` (details).
The committed snapshot, with findings per runtime, is [MATRIX.md](MATRIX.md).

**Benchmarks** run on the same runners: `python conformance/bench.py`
([BENCH.md](BENCH.md)). Each runner has a `bench` mode that times the
scenarios in `bench/scenarios.json`.

| Target | How it runs (all offline) |
|---|---|
| `python:run`, `python:run_async` | `codeupipe.core` Pipeline, sync and async entry points |
| `python:static-steps`, `python:static-inline` | `codeupipe.lower` fast export, loaded from disk (no State or Hooks: ✅\*) |
| `python:static-observe` | `codeupipe.lower` export with `observe=True`: State and Hooks judged too |
| `go:run` | `go run` against `runtimes/go`, `GOPROXY=off` |
| `ts:run`, `ts:run_async` | Bun runs `runtimes/ts/src` directly (no npm install) |
| `rs:run` | standalone crate, path dependency on `runtimes/rs` |
| `kt:run` | `kotlinc` on `runtimes/kt` sources (no Gradle) |
| `cs:run` | console project referencing `runtimes/cs` (local NuGet cache) |
| `cpp:run` | header-only `runtimes/cpp`, compiled with the system C++ compiler |

## Statuses

| | meaning |
|---|---|
| ✅ | every expectation matched |
| ✅* | everything the target *can observe* matched. Static code has no State or Hooks, so those checks cannot run |
| ❌ | something observable differed |
| ➖ | the target cannot express the case (e.g. export refuses a nested pipeline). Never counted as a pass |

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

Every case also checks, implicitly, that **the caller's input was not mutated**.
Numbers compare as JSON numbers (`1 == 1.0`), but `true` is never `1`.

### Reference vocabulary (each runner implements these natively)

| kind | op | behaviour |
|---|---|---|
| filter | `set` key, value | insert `key = value` |
| filter | `copy` from, to | insert `to = get(from)` (null if missing) |
| filter | `add` key, by | insert `key = get(key, 0) + by` |
| filter | `append` key, value | insert `key = copy(get(key) or []) + [value]` |
| filter | `fail` message | raise / return an error carrying `message` |
| filter | `remove` key | `remove(key)` |
| filter | `merge` value | `merge(Payload(value))` |
| filter | `has` key, to | insert `to = has(key)` |
| filter | `mutate` key, value | an in-place write: Python `insert(key, value)` as a statement, then return the payload |
| tap | `record` key | append `get(key)` to the runner's tap log |
| tap | `fail` message | fail the way that language's Taps fail (raise, panic) |
| valve `when` | `equals` key, value | `get(key) == value` |
| valve `when` | `truthy` key | `get(key)` is truthy (missing ⇒ false) |
| hooks | `"hooks": true` | record `before:<step>`, `after:<step>`, `error:<step>`; pipeline-level events use an empty step name. On a filter failure: `error:<step>` then `error:`. A runtime that reports step identities (API.md) maps them back to the case's step names in its runner |

## Runner protocol

`runner <target> < cases.json > results.json`. For each case the runner
emits `{"id", "output" | "error", "state"?, "taps", "hooks"?, "input_after"}`,
or `{"id", "unsupported": reason}`. Runners **never judge**.

Adding a runtime: implement the vocabulary, build pipelines from `steps`,
emit that shape, and register the command in `run.py`'s `TARGETS`. Runners
must not download anything; `go:run` runs with `GOPROXY=off`.

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
   No case depends on it yet.
