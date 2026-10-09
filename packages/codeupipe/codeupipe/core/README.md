# core

The foundation of codeupipe: the seven primitives — `Payload`, `Filter`,
`Pipeline`, `Valve`, `Tap`, `State`, `Hook` — plus supporting protocols,
governance and events. The export (`codeupipe.lower`) and the linter
(`codeupipe-lint`) are built on this package. No dependencies: standard
library only.

## Key files/classes

- `payload.py` — `Payload` (immutable data container; modifications return
  fresh copies) and `MutablePayload` (in-place variant for when flexibility
  is needed). Generic over a type parameter for type-safe workflows.
- `filter.py` — `Filter` (sync `Protocol`: `call(payload) -> payload`) and
  `AsyncFilter` (async opt-in). The core processing-unit contract.
- `stream_filter.py` — `StreamFilter`: chunk-at-a-time `Protocol` that yields
  zero or more output chunks per input chunk (filtering, mapping, fan-out).
  Regular Filters are auto-adapted to stream 1-in/1-out.
- `pipeline.py` — `Pipeline`, `CircuitOpenError`: the one orchestrator.
  `run()` / `stream()` are synchronous (the default) and never start an event
  loop; `run_async()` / `stream_async()` are the opt-in async entry points.
  Runs Filters in sequence, wires in Valves, Taps, Hooks, and State tracking,
  plus governance (schema, timeout, audit, dead-letter). Steps have no
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
- `hook.py` — `Hook` / `AsyncHook`: lifecycle ABC with `before`/`after`/
  `on_error` callbacks around filter and pipeline execution.
- `event.py` — `PipelineEvent`, `EventEmitter`: structured, OpenTelemetry-
  shaped events (`pipeline.start`, `step.end`, `circuit.open`, etc.)
  subscribable via `Pipeline.on(kind, callback)`.
- `govern.py` — Ring-6 pipeline guarantees: `PayloadSchema`/`SchemaViolation`
  (shape validation), `ContractViolation`, `PipelineTimeoutError`,
  `AuditEntry`/`AuditTrail`/`AuditHook` (immutable transformation log),
  `DeadLetterHandler`/`LogDeadLetterHandler` (route failed payloads).

## How it fits in

`core` imports nothing else from codeupipe. `codeupipe.lower` and
`codeupipe-lint` import from it, never the reverse. The data flow the
framework is built around is `Payload → Pipeline.run(payload)
→ Filter.call(payload) → Payload`.
