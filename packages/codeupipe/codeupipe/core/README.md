# core

This package holds the eight primitives: `Payload`, `Filter`, `Predicate`,
`Valve`, `Tap`, `Hook`, `State`, `Pipeline`. The contract is
[conformance/API.md](../../../../conformance/API.md). The compiler (`codeupipe.compile`) and the linter
(`codeupipe-lint`) are built on this package. No dependencies: standard
library only.

## Key files/classes

- `payload.py` — `Payload`: one keyed container. `insert`, `remove` and
  `merge` change it in place and return it; `copy()` gives a separate one.
- `filter.py` — `Filter` (sync `Protocol`: `call(payload) -> payload`) and
  `AsyncFilter` (async opt-in). The core processing-unit contract.
- `pipeline.py` — `Pipeline`: the one orchestrator. `add_filter`,
  `add_valve`, `add_tap`, `add_pipeline`, `use_hook`, `run`, `run_async`,
  `state`. `run()` is
  synchronous and never starts an event loop; `run_async()` is the opt-in
  entry point for async steps. Steps are not named by
  hand: each has a label, the name of its class (`step_label.py`), `#n` from
  the second use; State and Hooks report that label. A step without the
  method of its role is refused with a `TypeError` when it is added. See
  conformance/API.md, "Step labels".
- `step_label.py` — `label_of(step)`: the class name of a step; for a Valve,
  of its Filter.
- `async_step_in_sync_run.py` — `AsyncStepInSyncRun`: raised when the sync
  `Pipeline.run()` meets async work (it never starts an event loop).
- `predicate.py` — `Predicate`: a yes-or-no question about the payload, an
  object with `test(payload) -> bool`. It reads the payload and does not
  write to it.
- `valve.py` — `Valve`: the step that `Pipeline.add_valve(predicate, filter)`
  makes. The Filter runs only when the predicate is true; when it is false
  the payload passes through unchanged. Not a public name.
- `tap.py` — `Tap` / `AsyncTap`: read-only observation `Protocol`s
  (`observe(payload) -> None`); must not modify the payload.
- `state.py` — `State`: pipeline execution metadata — executed/skipped
  filters, timing, errors, arbitrary metadata. A State belongs to one run.
  `pipeline.state` is the State of the run that started last. A caller with
  more than one run at a time gives each run its own: `run(payload, state)`.
- `hook.py` — `Hook`: lifecycle ABC with `before`/`after`/`on_error`
  callbacks around filter and pipeline execution.
- `async_hook.py` — `AsyncHook`: a Hook whose methods are coroutines.

## How it fits in

`core` imports nothing else from codeupipe. `codeupipe.compile` and
`codeupipe-lint` import from it, never the reverse. The data flow the
framework is built around is `Payload → Pipeline.run(payload)
→ Filter.call(payload) → Payload`.
