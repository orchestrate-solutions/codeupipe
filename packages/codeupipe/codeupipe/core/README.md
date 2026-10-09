# core

This package holds the seven primitives: `Payload`, `Filter`, `Pipeline`,
`Valve`, `Tap`, `State`, `Hook`. The contract is
[conformance/API.md](../../../../conformance/API.md). The export (`codeupipe.lower`) and the linter
(`codeupipe-lint`) are built on this package. No dependencies: standard
library only.

## Key files/classes

- `payload.py` — `Payload`: one keyed container. `insert`, `remove` and
  `merge` change it in place and return it; `copy()` gives a separate one.
- `filter.py` — `Filter` (sync `Protocol`: `call(payload) -> payload`) and
  `AsyncFilter` (async opt-in). The core processing-unit contract.
- `pipeline.py` — `Pipeline`: the one orchestrator. `add_filter`, `add_tap`,
  `add_pipeline`, `use_hook`, `run`, `run_async`, `state`. `run()` is
  synchronous and never starts an event loop; `run_async()` is the opt-in
  entry point for async steps. Steps have no
  names: each is identified by its filter (`step_identity.py`), `#n` from
  the second use; State and Hooks report that identity. Nested pipelines are
  named `Pipeline` subclasses. See conformance/API.md, "Step identity".
- `step_identity.py` — derives a step's identity (`module.QualName`) and the
  `file:line` it was added at; refuses anonymous steps.
- `anonymous_step.py` — `AnonymousStep` (a `TypeError`): lambdas, closures,
  classes defined in a function, `__main__` filters, unnamed nested pipelines.
- `async_step_in_sync_run.py` — `AsyncStepInSyncRun`: raised when the sync
  `Pipeline.run()` meets async work (it never starts an event loop).
- `valve.py` — `Valve`: wraps a `Filter` with a predicate; the inner filter
  only runs when the predicate is true, otherwise the payload passes through
  unchanged. Conforms to `Filter`, so it composes into pipelines directly.
- `tap.py` — `Tap` / `AsyncTap`: read-only observation `Protocol`s
  (`observe(payload) -> None`); must not modify the payload.
- `state.py` — `State`: pipeline execution metadata — executed/skipped
  filters, timing, errors, arbitrary metadata. Available as `pipeline.state`
  after a run.
- `hook.py` — `Hook`: lifecycle ABC with `before`/`after`/`on_error`
  callbacks around filter and pipeline execution.
- `async_hook.py` — `AsyncHook`: a Hook whose methods are coroutines.

## How it fits in

`core` imports nothing else from codeupipe. `codeupipe.lower` and
`codeupipe-lint` import from it, never the reverse. The data flow the
framework is built around is `Payload → Pipeline.run(payload)
→ Filter.call(payload) → Payload`.
