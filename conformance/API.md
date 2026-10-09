# CUP API contract

> One standard way. The primitives, their operations, their parameters in
> order, their defaults, and how they fail.

Python implements it. A runtime in another language implements the same
contract, with identifier casing in that language's style, and is judged by
the same conformance cases.

## Principles

1. **Uniform semantics, uniform vocabulary.** A concept has one name. There
   is no second way to do the same thing.
2. **Native idioms are deferred, not rejected.** Indexers, operators and map
   protocols are out of scope for now. If added later they must be pure
   sugar over this vocabulary and must not change any semantics below.
3. **Sync is the default; async is opt-in.** A sync caller must never pay
   for an event loop.
4. **Every rule here is checked.** Semantics by the conformance cases; the
   vocabulary by the runner, which may only use the operations named here.
5. **A feature enters the contract with a conformance case**, and Core
   holds nothing that is not in the contract.

## Payload — keyed data

Keys are strings. Values are JSON-shaped: null, bool, number, string, list,
map. There is one Payload type. **A write changes the Payload and returns
it.** `copy()` gives a separate Payload for the caller who wants to keep the
one they have.

| Operation | Meaning | Python |
|---|---|---|
| construct | from a native map (copied) | `Payload(d)` |
| get | value, or `default`, or absent | `get(k, default=None)` |
| has | key present, also for a null value | `has(k)` |
| insert | set `k = v` in this payload; returns it | `insert(k, v)` |
| remove | remove `k` from this payload; returns it | `remove(k)` |
| merge | write `other` into this payload, `other` wins; returns it | `merge(other)` |
| copy | a separate payload, same contents | `copy()` |
| to_dict | native map copy | `to_dict()` |
| with_trace | set the trace id on this payload; returns it | `with_trace(id)` |
| trace_id, lineage | observation | `trace_id`, `lineage` |

**Absent** is the language's null: `None` in Python.

Rules:

- `insert`, `remove`, `merge` and `with_trace` **change the receiver and
  return it**, so a step can write and return in one line:
  `return payload.insert(k, v)`.
- `copy()` is shallow: the two payloads have separate keys and share their
  values. Change a nested value by copying it first.
- The caller's input map is never changed (copied on construct).
- **`run` works on a copy of the Payload it is given**, so the caller's
  Payload is not changed either.
- **Only a Filter writes.** A Tap, a Hook and a predicate read the
  Payload. To change the data, add a Filter. The linter is the guard
  (`CUP-I004`); the runtime does not check.
- A Tap, a Hook or a predicate that wants its own changed version, or that
  keeps the Payload for later, takes a `copy()`.

## Filter

`call(payload) -> payload`. A failure raises.

## Valve — a Filter gated by a predicate

`Valve(inner, predicate)`, identified by its inner filter (see "Step
identity"). The **predicate is an object** with `test(payload) -> bool`,
identified by its class like a step; any configuration (a threshold, a flag)
lives on the instance: `AtLeast("qty", 10)`. Functions, lambdas and closures
are not predicates. A predicate reads the Payload and does not write to it.
When `test` is false, the payload passes through unchanged and the step is
recorded in `state.skipped`, not `state.executed`. A Valve is added like any
filter: `add_filter(valve)`.

## Tap — reads the Payload (Plane B)

`observe(payload)`, no return value. A Tap reads the Payload and does not
write to it. **A Tap failure never halts the pipeline:** the error is
recorded in `state.errors` under the Tap's identity, the Tap still counts as
executed, and hooks are not notified.

## Hook — sees the lifecycle

`before(step, payload)`, `after(step, payload)`, `on_error(step, error, payload)`.
A Hook reads the Payload and does not write to it.

- `step` is the **step's identity** (see "Step identity"). Pipeline-level
  events pass absent (`None`).
- `error` is the error itself (never just its message).
- Order on success: `before(pipeline)`, then for each filter or Valve
  `before(step)`, `after(step)`, then `after(pipeline)`. Taps get no hook
  events.
- Order on a filter failure: `… before(step)`, `on_error(step)`,
  `on_error(pipeline)`. No `after` events follow.

## State — what happened in the last run

`executed` (identities, in order), `skipped` (identities), `errors`
(identity + error), `timings` (identity → seconds, when timing is on). A run
starts with a new State. **A failed run keeps the steps that completed
before the failure.**

## Pipeline

| Operation | Python |
|---|---|
| construct | `Pipeline()` |
| add a filter / Valve | `add_filter(f)` |
| add a tap | `add_tap(t)` |
| nest a pipeline | `add_pipeline(p)` |
| add a hook | `use_hook(h)` |
| run (sync) | `run(p)` |
| run (async, opt-in) | `run_async(p)` |
| last run | `state` |
| timing and lineage | `observe(timing=True, lineage=False)` |
| each step's identity, in order | `identities` |
| where each step was added (`file:line`) | `step_sites` |

- **Steps have no names.** State and Hooks report each step's identity.
- **`run` is synchronous** and never starts an event loop. If it meets an
  async step it raises `AsyncStepInSyncRun` rather than silently paying for
  a loop.
- A nested pipeline is one step: its identity appears once in the parent's
  State.
- **Timing and lineage are off by default.**

## Step identity: the filter, not a name

A step's identity is a pointer to the code that runs it, derived
automatically: `add_filter(f)`, not `add_filter(f, name)`. State, Hooks and
exported code all report this identity.

Why: in a codebase maintained by agents and reviewed by humans, an identity
taken from the code cannot drift from it. A hand-written name is an
unchecked label that can describe code which no longer matches it; a pointer
to the filter is always true, more specific, and needs no one to maintain
it.

### The identity

- **The filter's fully qualified symbol** (`app.filters.Validate`), plus an
  **occurrence number only when the same identity appears more than once**
  in one pipeline: the second is `...Validate#2`. Stable across unrelated
  edits.
- **Extra detail, not identity**: the source location of the `add_*` call
  (`file:line`), for agents and reviewers.
- **Valves**: the inner filter's identity; the Valve and its predicate's
  symbol are extra detail.
- **Pipelines used as a step are named types**: `class UserOnboarding(Pipeline)`,
  identified by that type's symbol exactly as a filter is. A plain, unnamed
  `Pipeline` can run at the top level but cannot be nested.
- Renames and moves change the identity. That is honest (it is different
  code); cross-version comparisons follow renames from version control.
- A filter defined in the entry script (`__main__.X`) is refused like an
  anonymous one: its identity changes with how the program is started, and
  tests cannot import it.

### Anonymous filters are unsupported

Lambdas, closures, classes defined inside a function, inline functions: as
filters, taps, valve predicates or nested pipelines. They are not
independently testable and have no stable identity. Enforced in two layers:

1. **The runtime refuses them** at `add_*` time (`AnonymousStep`), with a
   message naming the fix.
2. **The linter flags them** at authoring time:
   `python -m codeupipe_lint.anonymous_steps <paths...>`. One line per
   anonymous step, `path:line:col  CUP-A00N slug  message`; exit 1 when it
   finds any. An intentional one (a test of the refusal) is suppressed with
   a `cup: allow-anonymous` comment. Rules and limits:
   [packages/codeupipe-lint/README.md](../packages/codeupipe-lint/README.md).

**Conformance.** The shared cases name their steps; the runner builds every
step, so it maps each reported identity back to the case's step name. An
identity that is wrong, or differs between the dynamic run and an export,
does not map and fails the comparison.

## Not in the contract yet

- **Native idioms** (principle 2): the `Mapping` protocol, indexers,
  operators.
- **Parallel steps and streaming.** They join the contract when conformance
  cases exist for them.
- **Detaching async Taps** from the result. It needs its own decision, since
  it changes timing for callers who wait on a Tap's side effect.
- **Other runtimes.** A runtime in another language is written to this
  contract and added with its conformance runner.
