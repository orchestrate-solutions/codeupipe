# Typed Pipeline Rollout

Status of `TypedPipeline<Ctx>` across the six official CUP runtimes.

The typed API is **opt-in and additive** to the dynamic `Pipeline` API.
Same seven primitives, same manifesto invariants — the payload is a
concrete type known at authoring time instead of a dict.

Escape hatch: use `dict` / `Record<string, unknown>` / `HashMap` /
`interface{}` / `object` as `Ctx` if you need a dynamic bag of keys.

## Completed

| Runtime | Module | Tests | Fast-path hop |
|---|---|---|---|
| Rust | [`runtimes/rs/src/typed/`](rs/src/typed) | 10 | **4.2–4.6 ns/hop** (vs 190 ns dynamic — 42× faster) |
| Python | [`codeupipe/core/typed/`](../codeupipe/core/typed) | 15 | (not benched — Python interpreter dominates) |
| TypeScript | [`runtimes/ts/src/typed/`](ts/src/typed) | 12 | (not benched — v8 async dominates) |

All three ship the same shape:

```
TypedPipeline<Ctx>
  .add_filter(TypedFilter<Ctx>, name)
  .add_tap(TypedTap<Ctx>, name)
  .use_hook(TypedHook<Ctx>)
  .disable_taps(name...)
  .observe(timing=true|false)
  .run(ctx) -> ctx
```

## Follow-up scope

Not implemented this pass. Design notes below for the next agent turn.

### Go — `Pipeline[T any]`

Go 1.18+ generics work but use **GCShape dictionary passing**: a single
generic function body is instantiated once per GCShape (roughly, per
pointer-vs-value distinction), with a runtime dictionary of method
tables. So the wins are modest — probably **2–5×** over the current
`map[string]any` pipeline, not 40×.

- File: `runtimes/go/codeupipe/typed/pipeline.go`
- Types: `Filter[T any]`, `Tap[T any]`, `Valve[T any]`, `Hook[T any]`, `Pipeline[T any]`
- Interface constraint: `Filter[T any] interface { Call(ctx T) (T, error) }`
- Fast path parallels the existing `_canRunFast()`

### C# — `TypedPipeline<TCtx>`

Reified generics + potential for `readonly struct` context (zero
boxing, stack allocation, SIMD-friendly layout).

- File: `runtimes/cs/CupPipe/Typed/TypedPipeline.cs`
- Interfaces: `ITypedFilter<TCtx>`, `ITypedTap<TCtx>`, `ITypedHook<TCtx>`
- Recommend documenting the `readonly struct TCtx` pattern in the readme
- Expected **30–100×** improvement when `TCtx` is a struct

### Kotlin — `TypedPipeline<Ctx>`

Kotlin generics erase to JVM (like Java) but **inline value classes**
sidestep boxing for single-field wrappers.

- File: `runtimes/kt/codeupipe-core/src/main/kotlin/typed/TypedPipeline.kt`
- Interfaces: `TypedFilter<Ctx>`, `TypedTap<Ctx>`, `TypedHook<Ctx>`
- Recommend documenting `@JvmInline value class` for wrappers
- Expected **5–20×** improvement, more if Ctx is `@JvmInline`

## Contract (all runtimes)

- `TypedFilter<Ctx>.call(ctx) -> ctx` — pure transform
- `TypedTap<Ctx>.observe(ctx)` — read-only, must not mutate
- `TypedValve<Ctx>` — wraps a filter, records `lastSkipped` when the
  predicate returns false; pipeline consults `lastSkipped` in both
  full and fast paths
- `TypedHook<Ctx>` — `before/after(step, ctx)` and `onError(step, err)`.
  `on_error` receives no ctx — use a Tap upstream to snapshot ctx on
  error. Matches the manifesto ("hooks are lifecycle, not state").
- Fast path skips hooks/timing/taps when none are configured
- Manifesto invariants preserved:
  1. Removing every Tap yields identical output
  2. Same ctx through same pipeline yields same output
