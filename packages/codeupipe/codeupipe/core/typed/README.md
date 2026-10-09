# core/typed

A parallel, typed-payload API to `codeupipe.core`. Same seven-primitive
shape (Filter, Tap, Valve, Hook, State, Payload, Pipeline), but the payload
IS your type (`Ctx`) — a dataclass, `TypedDict`, Pydantic model, or anything
else — instead of a dynamic dict. Use `Ctx = dict` as an escape hatch to fall
back to the dynamic mental model.

## Key files/classes

- `filter.py` — `TypedFilter[Ctx]`: abstract `call(ctx) -> ctx`, same
  contract as `Filter` but over `Ctx` directly.
- `tap.py` — `TypedTap[Ctx]`: abstract `observe(ctx) -> None`; must not
  mutate `ctx` — removing every Tap must yield identical pipeline output.
- `valve.py` — `TypedValve[Ctx]`: a `TypedFilter` that gates an inner
  `TypedFilter` with `predicate(ctx)`; skipped runs return `ctx` unchanged
  and record `'skipped'` in State.
- `hook.py` — `TypedHook[Ctx]`: lifecycle callback (before/after per step and
  pipeline, on_error). `on_error` receives only the error, not `ctx` — use a
  `TypedTap` upstream to snapshot `ctx` if needed.
- `pipeline.py` — `TypedPipeline[Ctx]`: orchestrator with the same shape as
  `Pipeline` (filters, taps, valves, hooks, State), preserving the two core
  invariants: removing every Tap yields identical output, and the same
  `ctx` through the same pipeline yields the same output.

## How it fits in

Mirrors `core`'s untyped API one-for-one so the two can be chosen between per
project without relearning the model; gains are ergonomic (type-checker
visibility) rather than runtime performance, since Python has no
monomorphization. Keeping the API identical across both is part of CUP's
polyglot promise (the same shape recurs across runtimes).
