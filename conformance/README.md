# Conformance suite

The rules are in **[API.md](API.md)**, the CUP API contract. This suite
checks them.

One set of language-neutral cases, a runner, and **one judge** (`run.py`).
The dynamic run and each static export are held to exactly the same
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

**The speed check** compares each benchmark number with its recorded
baseline (`bench/baseline.json`):

```bash
python conformance/bench.py --check                  # fails outside ±25%
python conformance/bench.py --check --tolerance 15
python conformance/bench.py --record                 # after a change in speed that you accept
python -m pytest -m perf                             # the same check, as a test
```

A number is kept as a ratio to a reference workload (plain dict writes
behind function calls) that the runner times beside it, so the check does
not depend on how fast the machine is. Slower than the band is a regression.
Faster than the band also fails, with the instruction to record again:
otherwise the next regression would hide inside the gain. There is one
baseline for each Python version. Run it on a quiet machine: under heavy
load a number can leave the band.

| Target | How it runs (all offline) |
|---|---|
| `python:run`, `python:run_async` | `codeupipe.core` Pipeline, sync and async entry points |
| `python:static-steps`, `python:static-inline` | `codeupipe.lower` fast export, loaded from disk (no State or Hooks: ✅\*) |
| `python:static-observe` | `codeupipe.lower` export with `observe=True`: State and Hooks judged too |
| `typescript:run` | `packages/codeupipe-ts` Pipeline. Node runs the `.ts` runner as it is (Node 22.18 or later). With no arguments, `run.py` leaves this target out when the machine has no such Node |

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
   No case depends on it yet.
4. **`truthy` across languages.** An empty list or map is false in Python
   and true in JavaScript. Each runner uses the rule of its language. No
   case depends on it yet.
