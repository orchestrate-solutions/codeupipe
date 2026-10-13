# CUP API contract

This document defines the eight primitives, their operations, their
parameters, their defaults, and how they fail.

| Primitive | What it does |
|---|---|
| Payload | carries the data |
| Filter | changes the data |
| Predicate | asks a yes-or-no question about the data |
| Valve | joins a Predicate to a Filter |
| Tap | reads the data as it goes by |
| Hook | sees the lifecycle of a run |
| State | records what happened |
| Pipeline | runs the steps in order |

Python and TypeScript implement it. Each runtime has the same contract,
with identifier casing in the style of its language, and the same
conformance cases judge it. The tables below show the Python names. The
TypeScript names and differences are in "Runtimes".

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
- **Only a Filter writes.** A Tap, a Hook and a Predicate read the
  Payload. To change the data, add a Filter. The linter is the guard
  (`CUP-I004`); the runtime does not check.
- A Tap, a Hook or a Predicate that wants its own changed version, or that
  keeps the Payload for later, takes a `copy()`.

## Filter

`call(payload) -> payload`. A failure raises.

## Predicate — a yes-or-no question

`test(payload) -> bool`.

- A Predicate is an object. Its class gives it its name, and
  any setting (a threshold, a flag) is on the instance:
  `AtLeastPredicate("qty", 10)`. Functions, lambdas and closures are not
  Predicates.
- A Predicate reads the Payload and does not write to it.
- One Predicate can be used in many Valves.

## Valve — joins a Predicate to a Filter

A Valve is added with one call, the condition first:

    pipeline.add_valve(predicate, filter)

- When `predicate.test(payload)` is true, the Filter runs. When it is false,
  the Payload passes through unchanged and the step is recorded in
  `state.skipped`, not `state.executed`.
- The step has the label of its Filter (see "Step labels").
- `add_valve` is the one way to add a Valve. There is no Valve class for a
  user to make, and `add_filter` does not accept one.

## Tap — reads the Payload (Plane B)

`observe(payload)`, no return value. A Tap reads the Payload and does not
write to it. **A Tap failure never halts the pipeline:** the error is
recorded in `state.errors` under the Tap's label, the Tap still counts as
executed, and hooks are not notified.

## Hook — sees the lifecycle

`before(step, payload)`, `after(step, payload)`, `on_error(step, error, payload)`.
A Hook reads the Payload and does not write to it.

- `step` is the **step's label** (see "Step labels"). Pipeline-level
  events pass absent (`None`).
- `error` is the error itself (never just its message).
- Order on success: `before(pipeline)`, then for each filter or Valve
  `before(step)`, `after(step)`, then `after(pipeline)`. Taps get no hook
  events.
- Order on a filter failure: `… before(step)`, `on_error(step)`,
  `on_error(pipeline)`. No `after` events follow.

## State — what happened in one run

`executed` (labels, in order), `skipped` (labels), `errors`
(label + error), `timings` (label → seconds, when timing is on). **A failed
run keeps the steps that completed before the failure.**

**A State belongs to one run, not to the Pipeline.**

- Each run writes into a State of its own. Two runs of one Pipeline that
  are in progress at the same time never write into the same State.
- The caller can give the State: `run(p, state)`. The run writes into that
  State. This is how a caller with more than one run at a time gets the
  State of each run. The caller gives a new State for each run.
- With no State from the caller, the run makes a new one.
- `state` on the Pipeline is the State of the run that started last, with
  a State from the caller or not. It is for a caller that has one run at a
  time.

## Pipeline

| Operation | Python |
|---|---|
| construct | `Pipeline()` |
| add a filter | `add_filter(f)` |
| add a valve | `add_valve(predicate, filter)` |
| add a tap | `add_tap(t)` |
| nest a pipeline | `add_pipeline(p)` |
| add a hook | `use_hook(h)` |
| run (sync) | `run(p)`, `run(p, state)` |
| run (async, opt-in) | `run_async(p)`, `run_async(p, state)` |
| the State of the run that started last | `state` |
| timing and lineage | `observe(timing=True, lineage=False)` |
| each step's label, in order | `labels` |

- **Steps are not named by hand.** State and Hooks report each step's label.
- **`run` is synchronous** and never starts an event loop. If it meets an
  async step it raises `AsyncStepInSyncRun` rather than silently paying for
  a loop.
- A nested pipeline is one step: its label appears once in the parent's
  State.
- **Timing and lineage are off by default.**

## Step labels

A step is reported by a label. The label is the name of the step's class:
`add_filter(ValidateFilter())` gives the label `ValidateFilter`. State and
Hooks report this label. A step is not given a name by hand:
`add_filter(f)`, not `add_filter(f, name)`.

- **A second use gets a number.** When the same label is in one pipeline
  more than once, the second is `ValidateFilter#2`, the third
  `ValidateFilter#3`.
- **A Valve** has the label of its Filter.
- **A nested pipeline** has the label of its class. Make it a named type
  (`class UserOnboarding(Pipeline)`), so that the label says what it is. A
  plain `Pipeline` that is nested has the label `Pipeline`.
- A label is for people and for records. It does not say where the class is
  defined, and two classes with the same name in different modules have the
  same label.

### What is refused when a step is added

A step must have the method of its role. `add_filter` needs `call(payload)`,
`add_tap` needs `observe(payload)`, `add_valve` needs a predicate with
`test(payload)` and a Filter with `call(payload)`, and `add_pipeline` needs a
Pipeline. A value without that method (a lambda, a plain function) is
refused with a `TypeError` that names the method.

### What the linter flags

A step that is a lambda, a function, a class defined inside a function, or a
plain nested `Pipeline` cannot be imported and tested alone, and its label
says little. The linter flags these when the code is written:
`python -m codeupipe_lint.anonymous_steps <paths...>`. One line per finding,
`path:line:col  CUP-A00N slug  message`; exit 1 when it finds any. An
intentional one is suppressed with a `cup: allow-anonymous` comment. Rules
and limits:
[packages/codeupipe-lint/README.md](../packages/codeupipe-lint/README.md).

**Conformance.** The shared cases name their steps; the runner builds every
step, so it maps each reported label back to the case's step name. A label
that is wrong, or differs between the dynamic run and compiled code, does not
map and fails the comparison.

## Not in the contract yet

- **Native idioms** (principle 2): the `Mapping` protocol, indexers,
  operators.
- **Parallel steps and streaming.** They join the contract when conformance
  cases exist for them.
- **Detaching async Taps** from the result. It needs its own decision, since
  it changes timing for callers who wait on a Tap's side effect.
- **Other runtimes.** A runtime in another language is written to this
  contract and added with its conformance runner.

## Runtimes

| | Python | TypeScript |
|---|---|---|
| Package | `packages/codeupipe` | `packages/codeupipe-ts` |
| Names | snake_case | camelCase: `addFilter`, `addValve`, `toDict`, `withTrace`, `traceId`, `onError` |
| Run | `run` is sync. `run_async` is opt-in | One `run`. It returns a Promise. A step can be sync or async |
| Absent | `None` | `null` |
| Label of a step | `type(step).__name__` | `step.constructor.name` |
| Compile | `codeupipe.compile` | `packages/codeupipe-compile-ts` |
| Linter | `packages/codeupipe-lint` | `packages/codeupipe-lint-ts` |

Notes on TypeScript:

- **Principle 3.** JavaScript always has an event loop, so there is no
  second entry point. Inside `run`, a step that returns a value and not a
  Promise is not awaited.
- **A function is not a step.** Every JavaScript function has a `call`
  method, so a step must be an object.
- **Labels in minified code.** A minifier changes class names. A label is
  then the changed name, unless the build keeps class names. A class with no
  name has the label `anonymous`.
- **State and concurrent runs.** Two runs of one pipeline at the same time
  each write to their own State. `state` is the State of the run that
  started last.
