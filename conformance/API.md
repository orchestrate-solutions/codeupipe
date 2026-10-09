# CUP API contract

> One standard way, in every runtime. Same primitives, same operations, same
> parameters in the same order, same defaults, same failure behaviour.
> Only identifier casing follows each language (`add_filter` / `addFilter` /
> `AddFilter`).

Every runtime implements it. The conformance matrix ([MATRIX.md](MATRIX.md))
shows where each one stands.

## Principles

1. **Uniform semantics, uniform vocabulary.** A concept has one name,
   cased per language. No runtime adds a second way to do the same thing.
2. **Native idioms are deferred, not rejected.** Indexers, operators,
   language map protocols and comma-ok reads are out of scope for now. If
   added later they must be pure sugar over this vocabulary and must not
   change any semantics below.
3. **Sync is the default; async is opt-in.** A sync caller must never pay
   for an event loop.
4. **Every rule here is checked.** Semantics by the conformance cases; the
   vocabulary by the runners, which may only use the operations named here.

## Payload — immutable keyed data

Keys are strings. Values are JSON-shaped: null, bool, number, string, list,
map.

| Operation | Meaning | Python | TypeScript | Go | Rust | Kotlin | C# | C++ |
|---|---|---|---|---|---|---|---|---|
| construct | from a native map (copied) | `Payload(d)` | `new Payload(o)` | `NewPayload(m)` | `Payload::from_data(m)` | `Payload(m)` | `new Payload(d)` | `Payload(m)` |
| get | value, or `default`, or **absent** | `get(k, default=None)` | `get(k, default = null)` | `Get(k, default...)` | `get(k) -> Option`, `get_or(k, default)` | `get(k, default)` | `Get(k, default)` | `get(k[, default])` |
| insert | **new** payload with `k = v` | `insert(k, v)` | `insert(k, v)` | `Insert(k, v)` | `insert(k, v)` | `insert(k, v)` | `Insert(k, v)` | `insert(k, v)` |
| remove | **new** payload without `k` | `remove(k)` | `remove(k)` | `Remove(k)` | `remove(k)` | `remove(k)` | `Remove(k)` | `remove(k)` |
| merge | **new** payload, right side wins | `merge(other)` | `merge(other)` | `Merge(other)` | `merge(other)` | `merge(other)` | `Merge(other)` | `merge(other)` |
| has | key present | `has(k)` | `has(k)` | `Has(k)` | `has(k)` | `has(k)` | `Has(k)` | `has(k)` |
| to_dict | native map copy | `to_dict()` | `toDict()` | `ToDict()` | `to_dict()` | `toDict()` | `ToDict()` | `to_dict()` |
| with_trace | **new** payload with trace id | `with_trace(id)` | `withTrace(id)` | `WithTrace(id)` | `with_trace(id)` | `withTrace(id)` | `WithTrace(id)` | `with_trace(id)` |
| trace_id, lineage | observability | `trace_id`, `lineage` | `traceId`, `lineage` | `TraceID()`, `Lineage()` | `trace_id()`, `lineage()` | `traceId`, `lineage` | `TraceId`, `Lineage` | `trace_id()`, `lineage()` |
| with_mutation | a `MutablePayload` copy | `with_mutation()` | `withMutation()` | `WithMutation()` | `with_mutation()` | `withMutation()` | `WithMutation()` | `with_mutation()` |

**Absent** is the language's null: Python `None`, TypeScript `null` (never
`undefined`), Go `nil`, Rust `None`, Kotlin `null`, C# `null`, C++ the null
`Value`.

Rules that never differ:

- `insert`, `remove`, `merge`, `with_trace` **never change the receiver.**
  Where the language can enforce use of the result it must: C++
  `[[nodiscard]]`, Rust `#[must_use]`, C# `[Pure]`. Elsewhere `cup lint`'s
  no-discarded-insert rule covers it.
- A typed read of the wrong type **fails loudly**; it never returns absent.
- The caller's input map is never mutated (copied on construct).

### MutablePayload — the explicit mutable escape hatch

`get(k, default)`, `set(k, v)` (in place), `remove(k)` (in place),
`to_immutable()`. The name split is deliberate: `insert` returns a new
payload; `set` changes this one.

## Filter

`call(payload) -> payload`. Failure uses the language's error model:
Python/TypeScript/Kotlin/C#/C++ raise or throw; Go returns `(Payload, error)`;
Rust returns `Result<Payload, Error>`.

## Valve — a Filter gated by a predicate

`Valve(inner, predicate)`, identified by its inner filter (see "Step
identity"). The **predicate is an object** with `test(payload) -> bool`
(`Test` in Go and C#), identified by its class like a step; any
configuration (a threshold, a flag) lives on the instance. Functions,
lambdas and closures are not predicates. When `test` is false, the payload
passes through unchanged and the step is recorded in `state.skipped`, not
`state.executed`. A Valve is added like any filter: `add_filter(valve)`.

## Tap — read-only observer (Plane B)

`observe(payload)`, no return value. **A Tap failure never halts the
pipeline:** the error is recorded in `state.errors` under the Tap's name, the
Tap still counts as executed, and hooks are not notified. Taps fail the way
the language fails without an error return (raise, or panic in Go and Rust).

## Hook — lifecycle observer

`before(step, payload)`, `after(step, payload)`, `on_error(step, error, payload)`.

- `step` is the **step's name**, or its **identity** in a runtime that has
  migrated (see "Step identity"). Pipeline-level events pass **absent**
  (`None`/`null`); in Go and C++, whose strings are not nullable, the empty
  string.
- `error` is the error itself (never just its message).
- Order on success: `before(pipeline)`, then for each filter or Valve
  `before(step)`, `after(step)`, then `after(pipeline)`. Taps get no hook
  events.
- Order on a filter failure: `… before(step)`, `on_error(step)`,
  `on_error(pipeline)`. No `after` events follow.

## State — what happened in the last run

`executed` (names, in order), `skipped` (names), `errors` (name + error),
`timings` (name → seconds, when timing is on). A migrated runtime reports
identities in place of names. A run resets State. **A failed
run keeps the steps that completed before the failure.**

## Pipeline — one type per runtime

| Operation | Python | TypeScript | Go | Rust | Kotlin | C# | C++ |
|---|---|---|---|---|---|---|---|
| construct | `Pipeline()` | `new Pipeline()` | `NewPipeline()` | `Pipeline::new()` | `Pipeline()` | `new Pipeline()` | `Pipeline()` |
| add a filter / Valve | `add_filter(f, name)` | `addFilter(f, name)` | `AddFilter(f, name)` | `add_filter(f, name)` | `addFilter(f, name)` | `AddFilter(f, name)` | `add_filter(f, name)` |
| add a tap | `add_tap(t, name)` | `addTap(t, name)` | `AddTap(t, name)` | `add_tap(t, name)` | `addTap(t, name)` | `AddTap(t, name)` | `add_tap(t, name)` |
| nest a pipeline | `add_pipeline(p, name)` | `addPipeline(p, name)` | `AddPipeline(p, name)` | `add_pipeline(p, name)` | `addPipeline(p, name)` | `AddPipeline(p, name)` | `add_pipeline(p, name)` |
| add a hook | `use_hook(h)` | `useHook(h)` | `UseHook(h)` | `use_hook(h)` | `useHook(h)` | `UseHook(h)` | `use_hook(h)` |
| run (sync) | `run(p)` | `run(p)` | `Run(p)` | `run(p)` | `run(p)` | `Run(p)` | `run(p)` |
| run (async, opt-in) | `run_async(p)` | `runAsync(p)` | — | — | — | — | — |
| last run | `state` | `state` | `State()` | `state()` | `state` | `State` | `state()` |

- **Step names are required** and are what State and Hooks report, until
  a runtime migrates to step identity: then `add_filter(f)`, `add_tap(t)`,
  `add_pipeline(p)` take no name. **Migrated: Python.**
- **`run` is synchronous** and never starts an event loop. If it meets an
  async step it raises (Python's `AsyncStepInSyncRun`) rather than silently
  paying for a loop. `run_async` exists only where the runtime has async
  steps; a `run_async` that merely wrapped `run` would be async in name only.
- A nested pipeline is one step: its name (or identity) appears once in the
  parent's State.

## Step identity: the filter, not a name

**Decision.** Step names are removed. A step's identity is a pointer to the
code that runs it, derived automatically: `add_filter(f)`, not
`add_filter(f, name)`. State, Hooks, the event log and exported code all
report this identity. The rules above that mention names change when a
runtime migrates; until then they stand for it.

Why: in a codebase maintained by agents and reviewed by humans, an
identity taken from the code cannot drift from it. A hand-written name is
an unchecked label that can describe code which no longer matches it; a
pointer to the filter is always true, more specific, and needs no one to
maintain it.

Feasibility was probed in all seven runtimes before adopting the details
below.

### The identity

- **The filter's fully qualified symbol**, in the language's own form
  (`app.filters.Validate`, `example.com/app/filters.Validate`,
  `app::filters::Validate`, `App.Filters.Validate`), plus an **occurrence
  number only when the same identity appears more than once** in one
  pipeline: the second is `...Validate#2`. Stable across unrelated edits.
- **Extra detail, not identity**: the source location of the `add_*` call
  (`file:line`), for agents and reviewers.
- **Valves**: the inner filter's identity; the Valve and its predicate's
  symbol are extra detail.
- **Pipelines used as a step are named types**: `class UserOnboarding(Pipeline)`
  (or the language's equivalent), identified by that type's symbol exactly as
  a filter is. A plain, unnamed `Pipeline` can run at the top level but
  cannot be nested. Inside a nested pipeline, identities form a path:
  parent / child.
- Renames and moves change the identity. That is honest (it is different
  code); cross-version comparisons follow renames from version control.

### Per-language rules

- **TypeScript**: JS has no runtime module identity and minifiers rename
  classes, so identity is **stamped at build time** by codeupipe's build
  step (`src/filters.ts#Validate`), and the runtime reads the stamp. An
  unstamped filter is refused. Running the build step is required for every
  TypeScript consumer.
- **C++**: filters are **types** (structs/classes). A free function has no
  derivable name (a function pointer carries only its signature).
- **Python**: a filter defined in the entry script (`__main__.X`) is
  refused like an anonymous one: its identity changes with how the program
  is started, and tests cannot import it.
- **Rust**: `std::any::type_name` is best-effort across compiler versions;
  a toolchain upgrade can change identities. Pin the toolchain.

### Anonymous filters are unsupported

Lambdas, closures, anonymous classes, classes defined inside a function,
inline functions: as filters, taps, valve predicates or nested pipelines.
They are not independently testable and have no stable identity. Enforced
in two layers:

1. **The runtime refuses what it can detect**, at `add_*` time, with a
   message naming the fix (a named type or module-level function).
2. **The linter flags all of them** at authoring time, and is the only
   check where the runtime cannot see the difference:

| | lambda / closure | class defined in a function |
|---|---|---|
| Python | runtime | runtime |
| Kotlin | runtime | runtime |
| C# | runtime | n/a |
| Go | runtime | linter only |
| Rust | runtime | linter only |
| C++ | runtime | linter only |
| TypeScript (with the build step) | runtime | runtime |

The linter: `python -m codeupipe_lint.anonymous_steps <paths...>` (repo root). It
reports one line per anonymous step, `path:line:col  CUP-A00N slug  message`,
with a message naming the fix, and exits 1 when it finds any (2 when a
language's analyzer could not run). Rules `CUP-A001`..`CUP-A007` cover
lambdas and closures, local functions, local types, anonymous types, unnamed
nested pipelines, Python entry-script steps and C++ free functions. An
intentional one (a test of the refusal) is suppressed with a
`cup: allow-anonymous` comment. Methods and known limits per language:
[packages/codeupipe-lint/README.md](../packages/codeupipe-lint/README.md).

**Conformance.** The shared cases keep naming steps; a runner built every
step, so it maps each reported identity back to the case's step name. An
identity that is wrong, or differs between modes, does not map and fails the
comparison. (Python: `conformance/runners/python/runner.py`, `labels`.)

**Status.**

- Python: done (`packages/codeupipe/codeupipe/core/step_identity.py`; tests in
  `tests/core/test_step_identity.py`; export generates its own identifiers,
  `step_03_validate`, and reports identities as labels).
- TypeScript: done (`runtimes/ts/src/step_identity.ts` reads stamps; the
  build step is `runtimes/ts/identity/`, with adapters for vitest/Vite, Bun
  and tsc output; `runtimes/ts/README.md`). Stamps are placed where module-
  level code can already see them (a class right after its declaration, a
  hoisted function at the top of the module) without moving any line. With
  the build step, TypeScript's runtime enforcement is complete: anything
  not a stamped top-level declaration is refused, closures and local classes
  included, which supersedes the "linter only" cells for TypeScript below.
- Go: done. Types via `reflect`, functions via `runtime.FuncForPC` (both
  survive stripped builds). Nested pipelines are named types embedding
  `*Pipeline` (the `Nestable` interface). Refusals panic with
  `*AnonymousStep`. Types declared inside a function stay linter-only.
- Kotlin: done. `Pipeline` is `open`; the JVM marks lambdas, anonymous
  objects and local classes, so runtime enforcement is complete. Valve
  predicates are `fun interface Predicate` implemented by named types (a
  Kotlin function reference compiles to a synthetic class).
- C#: done. Type `FullName`; `Pipeline` unsealed; caller-info attributes
  for the add site (ordered so a leftover name argument fails to compile).
  Lambda/closure predicates refused; instance method groups carry
  configuration.
- Rust: done. `std::any::type_name` via generic `add_*`; `Box<dyn Filter>`
  and nesting a plain `Pipeline` (no `Nestable`) are compile errors;
  closures panic; `Predicate` trait (named fns, or structs with settings).
  Pin the toolchain.
- C++: done, enforced at compile time. Type names from
  `__PRETTY_FUNCTION__`/`__FUNCSIG__`; `static_assert` refuses lambdas,
  function-pointer predicates, anonymous-namespace types, `unique_ptr`
  steps and a plain nested `Pipeline`. Predicates are functor types.
- Remaining outside the contract: Rust's `WasmPipeline` (the JS bridge)
  still names its JS-callback steps; adopting the TypeScript build step's
  stamp there is a follow-up.

**Predicates are objects**: a class with
`test(payload) -> bool`, configuration on the instance
(`AtLeast(5)`), identified by its class. One shape in every runtime, and it
gives every runtime a configurable predicate without closures, which
function predicates could not (TypeScript had none; each other runtime had
its own workaround).

| runtime | predicate |
|---|---|
| Python | a class with `test(self, payload)`; export lowers `test` with the instance's literal settings compiled in, as for filters |
| TypeScript | a class implementing `Predicate` (`test(payload)`), stamped by the build step |
| Go | a named type implementing `Predicate` (`Test(Payload) bool`) |
| Kotlin | a class or object implementing `fun interface Predicate` |
| C# | a class implementing `IPredicate` (`bool Test(Payload)`) |
| Rust | a named type implementing `Predicate` (no blanket impl for fns) |
| C++ | a type with `bool test(const Payload&) const` |

## Not in the contract yet

- **Native idioms** (principle 2): Python's `Mapping` protocol, indexers,
  operators, Go comma-ok, `IReadOnlyDictionary`, etc.
- **`add_parallel` and `stream`.** They exist in several runtimes with
  differing semantics. They join the contract when conformance cases exist
  for them.
- **Detaching async Taps** from the result. It needs its
  own decision, since it changes timing for callers who wait on a Tap's side
  effect.
