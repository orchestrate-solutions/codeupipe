# Plan: codeupipe for Rust

This is a plan, not a reference. It says how the third runtime is added: a
Rust runtime with the same contract ([conformance/API.md](../conformance/API.md)),
judged by the same conformance cases, in the same layout as TypeScript.

**How it is built: from the contract, tests first.** Each behaviour starts as
a failing test that comes from a rule of the contract or from a test of the
TypeScript package. **When in doubt, do what the TypeScript package does**: it
is the reference for every question that the contract does not answer.

The Rust runtime in the old repository (`runtimes/rs`) is not the start. Its
API is from before version 2: steps named by hand, no Predicate, no labels.
It can be read for ideas. No code is copied from it.

## Versions

The Rust packages start at **0.1.0**, as the TypeScript packages did. A version
below 1.0 is not stable yet, and a new version can change in a way that is not
compatible. For Cargo that means: 0.1.x to 0.2.0 is a change that is not
compatible.

The packages are not on crates.io at first. Each has `publish = false`, as each
TypeScript package has `"private": true`. Until they are published, a project
uses them from this repository:

```toml
[dependencies]
codeupipe = { git = "https://github.com/orchestrate-solutions/codeupipe", branch = "beta" }
```

Cargo finds the crate by its name inside the repository, so this works with
the crate in `packages/codeupipe-rs`.

## Layout

The packages are beside the others, with `-rs` where TypeScript has `-ts`.

| Path | Crate | Contents | Phase |
|---|---|---|---|
| `packages/codeupipe-rs/` | `codeupipe` | The eight primitives. No dependencies | 1 |
| `conformance/runners/rust/` | (binary, not published) | The conformance runner, with its `cup_ops` steps | 2 |
| `packages/codeupipe-compile-rs/` | `codeupipe-compile` | Writes a pipeline as plain Rust with no use of codeupipe | 3 |
| `packages/codeupipe-lint-rs/` | `codeupipe-lint` | The linter for rules that the type system does not already check | 4 |

A root `Cargo.toml` makes the Rust crates one Cargo workspace. It is not a
package, as the root `package.json` is not a package. `Cargo.lock` is
committed, since the workspace has a binary (the runner). `target/` goes in
`.gitignore`.

One primitive is in each file, and the file name is the type name in
snake_case, as in Python: `DiscountFilter` is in `discount_filter.rs`.

### The core crate

```
packages/codeupipe-rs/
  Cargo.toml            name = "codeupipe", version = "0.1.0", publish = false
  README.md  LICENSE  NOTICE
  src/
    lib.rs              the public names, as index.ts has them
    value.rs            Value: null, bool, number, string, list, map
    payload.rs          Payload
    filter.rs           trait Filter
    predicate.rs        trait Predicate
    tap.rs              trait Tap
    hook.rs             trait Hook, every method with a default that does nothing
    state.rs            State
    valve.rs            Valve (not a public name)
    pipeline.rs         Pipeline
    named_pipeline.rs   trait NamedPipeline (see decision D1)
    step_label.rs       the label from the type name
    step_error.rs       the error type of a step (see decision D4)
  tests/
    payload.rs  pipeline.rs  step_label.rs  pricing_example.rs
  examples/pricing/
    main.rs  discount_filter.rs  mark_bulk_filter.rs  at_least_predicate.rs
    audit_tap.rs  print_steps_hook.rs  pricing_pipeline.rs
```

## Decisions

These are the questions that Rust raises and Python and TypeScript do not.
**They are settled as recommended** (2026-10-27).

### D1. A named pipeline

**The question.** The contract says to make a nested pipeline a named type
(`class UserOnboarding(Pipeline)`), so that its label says what it is. Rust has
no classes to extend.

**Recommendation.** A trait that a named type implements. Its one method adds
the steps. The label is the name of the type.

```rust
pub struct PricingPipeline;

impl NamedPipeline for PricingPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_filter(DiscountFilter::new(0.1));
        // MarkBulkFilter runs only when the predicate is true.
        pipeline.add_valve(AtLeastPredicate::new("qty", 10.0), MarkBulkFilter);
        // A Tap only reads. If it fails, State records the error and the run goes on.
        pipeline.add_tap(AuditTap);
    }
}

let mut pipeline = Pipeline::named(PricingPipeline);
```

`add_steps` is also what the compiler reads (phase 3), as the TypeScript
compiler reads the constructor. A plain `Pipeline::new()` has the label
`Pipeline`, as in the contract.

### D2. How a write returns the Payload

**The question.** The contract says that a write changes the Payload and
returns it, so that `return payload.insert(k, v)` is one line.

**Settled.** A Filter gets `&mut Payload` and writes in place. A write takes
`&mut self` and returns it, so writes chain:
`payload.insert("a", 1).remove("b")`.

```rust
fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
    let price = payload.get("price").and_then(Value::as_f64).unwrap_or(0.0);
    payload.insert("price", (price * (1.0 - self.rate) * 100.0).round() / 100.0);
    Ok(())
}
```

The first recommendation was by value: `call(payload: Payload) -> Result<Payload, _>`.
It was changed in phase 1, against the TypeScript package. TypeScript changes
the Payload in place, and its `onError` gets that same Payload, with the
writes the failing step made before it threw. By value, the Payload is gone
when the Filter fails, and `on_error` has none to give. `&mut` does what
TypeScript does, and a Filter cannot return a different Payload (which the
TypeScript compiler has to refuse).

A Tap, a Predicate and a Hook get `&Payload`. So **only a Filter can write, and
the compiler checks it**: lint rule `CUP-I004` (a write outside a Filter) is a
type error in Rust, not a lint finding.

### D3. `get` with a default

**The question.** The contract has `get(k, default)`. Rust has no default
arguments and no overloads.

**Recommendation.** `get(k) -> Option<&Value>`. A default is
`.unwrap_or(...)`, which is the language's own way, not a second name.
`Value` has `as_f64`, `as_str`, `as_bool`, `as_list`, `as_map`. Absent is
`None`.

### D4. Errors

**The question.** A Filter failure raises, the Hook gets "the error itself",
and State keeps (label, error).

**Recommendation.** A step returns `Result`. `StepError` is
`Box<dyn std::error::Error + Send + Sync>`. `on_error` gets `&StepError`, and
then `run` returns the same error. A Tap error goes into `state.errors`.

A **panic is not a failure**. It is not caught: a panicking Tap stops the run.
The README says so. Catching panics (`catch_unwind`) would make the Tap rule
hold for panics too, but it needs `UnwindSafe` bounds on every step. It can
be added later without changing the API.

### D5. Labels

**The question.** The label is the name of the step's type.

**Recommendation.** `add_filter<F: Filter + 'static>(&mut self, filter: F)`
reads `std::any::type_name::<F>()` when the step is added, and keeps the last
part of the path (`examples::pricing::DiscountFilter` gives `DiscountFilter`).
Generic arguments are dropped (`Wrapper<Inner>` gives `Wrapper`). A closure
does not implement `Filter`, so it cannot be a step. There is no blanket
implementation for `Fn`.

What the contract refuses with a `TypeError` when a step is added is a
compile error in Rust: a value without `call` does not implement `Filter`, and
`add_valve(filter, predicate)` does not type-check. Tests for these use
`compile_fail` doc tests, which need no dependency.

### D6. Values and the order of keys

**The question.** Values are JSON-shaped, and the core crate has no
dependencies, so there is no `serde_json::Value`.

**Recommendation.** An own `Value` enum: `Null`, `Bool`, `Number(f64)`,
`String`, `List(Vec<Value>)`, `Map(...)`. One number type, as JavaScript has,
and as the conformance judge compares (`1 == 1.0`).

Keys keep the order in which they were inserted, as a Python dict and a
JavaScript Map do. `to_dict` gives them in that order. The judge does not
compare order, so this is for people, not for conformance.

`copy()` is a deep copy in this version. The contract says the two Payloads
"share their values", but in Rust a shared value cannot be changed without a
`Cell` or a lock, so a deep copy shows the same behaviour. Sharing with `Rc`
can be added later for speed, without a change to the API.

### D7. Sync and async

**Recommendation.** 0.1.0 has `run` only, and it is sync (contract principle
3). A sync caller never pays for an executor. `run_async` waits for a
conformance case that needs it, and for a choice of how to stay free of
dependencies (an `async fn` in the traits, driven by the caller's executor).

### D8. State and the run

**Recommendation.** `run(&mut self, input: &Payload) -> Result<Payload, StepError>`.
It copies `input`, so the caller's Payload is not changed (contract), and it
writes a new `State` into the pipeline. `pipeline.state()` reads it.
`&mut self` means that two runs of one pipeline at the same time are not
possible. That is simpler than the TypeScript rule ("the run that started
last") and it needs no lock.

`timings` keeps a `Duration` for each label. `observe(timing, lineage)` takes
two `bool`s.

On `wasm32-unknown-unknown`, `std::time::Instant` panics. Timing is off by
default, so a pipeline runs in WebAssembly. Timing there is out of scope for
0.1.0, and the README says so.

### D9. Edition and Rust version

**Recommendation.** Edition 2021, `rust-version = "1.75"`. The core uses
nothing newer. This machine has 1.89.

### D10. The crate names

`codeupipe`, `codeupipe-compile` and `codeupipe-lint` are the names in the
other languages. Before the first publish, check that they are free on
crates.io. The old repository used `codeupipe-core`.

### D11. A payload of your own

**Settled (2026-10-27).** `Payload` stays the default: a map that any
developer can read, which shows that anything can go there. A developer, or
an agent, that would write a struct anyway can opt in: each primitive takes
the data type as a parameter with `Payload` as its default (`Filter<P =
Payload>`, `Pipeline<P = Payload>`), and the type implements `PipelineData`:
`Clone` (for the copy that `run` works on) and an optional `stamp` for
lineage. Code written for `Payload` does not change; `Pipeline::new()` infers
the type from its steps.

Python allows the same by duck typing (its Pipeline calls only `copy()`, and
`_stamp()` when lineage is on); TypeScript has no such option. A step for one
type in a pipeline of another is a compile error, checked by a doc test.

Measured (release, Apple Silicon): the pricing pipeline runs in 0.024 µs
with an `Order` struct against 0.18 µs with a Payload, and 50 writes take
0.46 µs against 4.3 µs. What is left, about 9 ns a step, is the pipeline's own
work: State, Hooks and the call through `dyn Filter`.

## Phase 1: the core crate

**Done** (2026-10-27): `packages/codeupipe-rs`, 47 tests (16 Payload, 17
Pipeline, 7 labels, 3 example, 4 doc tests, 3 of them `compile_fail`),
`cargo clippy -- -D warnings` and `cargo fmt --check` clean. The tests are
ported from `packages/codeupipe-ts/tests`, except those that have no Rust form:
async steps, two runs at the same time, a class with no name, a key named like
an Object property.

The eight primitives, to the contract, with the decisions above.

Steps:

1. `value.rs` and `payload.rs`, with tests first (RED, GREEN, REFACTOR), from
   the Payload table of the contract.
2. The traits: `Filter`, `Predicate`, `Tap`, `Hook`. `step_label.rs`.
3. `State`, `Valve`, `Pipeline` (`add_filter`, `add_valve`, `add_tap`,
   `add_pipeline`, `use_hook`, `run`, `state`, `labels`, `observe`), and
   `NamedPipeline`.
4. The pricing example, with its test, giving
   `{"price": 90.0, "qty": 12.0, "bulk": true}`.
5. The README, in the form of the TypeScript README: the primitives, the
   example, the names, the differences from Python.

Done when: `cargo test`, `cargo clippy -- -D warnings` and `cargo fmt --check`
pass, and `cargo run --example pricing` prints the result and the State.

## Phase 2: conformance

**Done** (2026-10-27): `rust:run` passes all 27 cases, with nothing
unsupported. To check that the runner catches a broken runtime, the core was
changed so that it did not record a Tap failure: 3 cases failed. The runner
has 7 tests of its JSON reader and writer. `bench.py` measures `rust:run`, its
baseline is kept under its own key (`rust`, not a Python version), and CI has a `rust` job, which also
builds with Rust 1.75 (D9).

One thing that only Rust needed: `add_filter` and `add_valve` take the type
of the step, which gives its label. A step that the runner picks at run time
cannot be a `Box<dyn Filter>` (its label would be `Box`), so the runner hands
each Filter over by its own type through a small generic trait (`UseFilter`).

The first numbers showed `rust:run` 4 to 5 times faster than `python:run`
but about 2 times **slower** than compiled Python. The time was in
allocation, not in dispatch (50 no-op steps take 0.42 µs). Three changes to
the core, with no change to its behaviour or its API:

1. **`Map::insert` looks the key up first**, so a key that is there makes no
   new `String`.
2. **State keeps its storage between runs** and writes the labels over, so a
   run like the last one makes no new label `String`.
3. **A key is an `Arc<str>`, made once**, shared by the index and by every
   copy of the map. A map of 8 keys or fewer is searched in order and has no
   hash index; a larger one gets an index with room to grow. The hash stays
   std's SipHash: a faster hasher with no random seed would let crafted keys
   slow down a map that is read from untrusted JSON.

µs per run, Apple Silicon, one run:

| scenario | python:run | python:static-inline | rust:run before | rust:run now |
|---|---|---|---|---|
| `micro-pass` (10 filters) | 4.94 | 0.606 | 1.10 | 0.246 |
| `valve-gated` | 5.81 | 0.801 | 1.24 | 0.301 |
| `taps` | 5.34 | 0.602 | 1.17 | 0.256 |
| `hook` | 5.88 | — | 1.10 | 0.247 |
| `heavy-allocation` (50 inserts) | 16.05 | 1.49 | 7.26 | 4.24 |

The dynamic Rust run is now 20 times faster than `python:run`, and 2.5 times
faster than compiled Python, except where a run makes 50 new keys: there each
new key is an allocation and a hash, and a Python dict is hard to beat. **So
phase 3 waits**: the dynamic run already costs about 25 ns a step, and a
compiler would remove nanoseconds that few pipelines would notice. The README
says "no compiler yet".

A runner in `conformance/runners/rust/`, with the protocol of the others:
`runner <target> < cases.json > results.json`. It never judges.

- **Steps.** `cup_ops/` has one file for each step type, with the names that
  the TypeScript runner uses: `SetFilter`, `CopyFilter`, `AddFilter`,
  `AppendFilter`, `RemoveFilter`, `MergeFilter`, `HasFilter`, `MutateFilter`,
  `FailFilter`, `RecordTap`, `FailTap`, `NoopTap`, `EqualsPredicate`,
  `TruthyPredicate`, `RecordHook`, `NestedPipeline`.
- **JSON.** The runner has its own small JSON reader and writer. A runner must
  not download anything, so `serde_json` is not used. The core crate does not
  get JSON either: principle 5 says that core holds nothing that is not in the
  contract.
- **`run.py`.** A `_rust(target)` entry runs
  `cargo run --quiet --release --offline --manifest-path conformance/runners/rust/Cargo.toml -- <target>`.
  `default_targets()` leaves out `rust:*` when there is no `cargo`, as it
  leaves out TypeScript when there is no Node 22.18. The target `rust:run` is
  added to `TARGETS`.
- **Benchmark.** `rust:run` is added to `bench.py`. Its number, beside
  `python:run` and the compiled Python forms, decides phase 3 (below).
- **CI.** A `rust` job in `ci.yml`: `cargo fmt --check`, `cargo clippy`,
  `cargo test`, the example, and `python conformance/run.py rust:run`.
- **Documents.** A Rust column in the "Runtimes" table of API.md, a row in the
  README's table of packages, and `rust:run` in MATRIX.md.

Done when: `rust:run` passes all 27 cases, with nothing unsupported.

Open questions 3 and 4 of the conformance README (`equals` and `truthy`
across languages) get a Rust answer here. Recommendation: `equals` compares
`Value` by content, and `truthy` follows Python (an empty list or map is
false). No case depends on them yet.

## Phase 3: compile

`codeupipe-compile` for Rust: it reads the source of a named pipeline and
writes one plain Rust module with no use of codeupipe. Same rule as the
others: **code that compiles gives the same output as the pipeline; a shape
that cannot keep that rule is refused, with the place named.** It is a
codeupipe pipeline itself, as the TypeScript compiler is:

```
ResolvePipelineFilter   the add_steps body to a list of steps (a nested pipeline flattened)
LowerStepsFilter        each step to a plain function
EmitModuleFilter        the functions to one module
```

It depends on `syn` (to read Rust) and `prettyplease` (to write it), as the
TypeScript compiler depends on `typescript`. The core crate stays without
dependencies.

```bash
codeupipe-compile src/pricing_pipeline.rs:PricingPipeline --out src/compiled/pricing.rs
```

Exit codes as in TypeScript: 0 written, 1 refused, 2 could not run.

### Before it starts: is it worth it?

In Python the compiled code is 6 to 8 times faster than the dynamic run,
because it removes the interpreter's work. Rust's dynamic run is already
machine code. What a compile removes in Rust is the State, the label strings,
the Hook loop and the call through `dyn Filter`. That could be 2 to 3 times,
or less. **Phase 2 measures `rust:run` first. Phase 3 starts only if the
number leaves room for a gain that is worth a compiler.** If it does not, the
compiler waits, and the Rust row in the README says "no compiler".

Measured in phase 2 (2026-10-27): it does not, for now. After the work on the
core, a dynamic step costs about 25 ns, and the dynamic run is faster than
compiled Python in four of the five scenarios. The compiler waits until a
real pipeline shows a need.

### The value type in compiled code

Plain Python has `dict`, and plain TypeScript has `Map`. Plain Rust has no
JSON-shaped value. So the compiled module must carry one: a small `Value` enum
and its map, written into the module (about 60 lines). It is not an import of
codeupipe, so the rule holds, but it is code that the compiler writes and
that must stay the same as the core's `Value`. A test checks that the two
behave the same.

### What compiles and what is refused

The tables of the TypeScript compiler, in Rust:

| Shape | Plain form |
|---|---|
| A named pipeline (`impl NamedPipeline`) | `pub fn run(input: &Map) -> Result<Map, StepError>`. `add_steps` holds only `add_*` calls |
| Filter (`call`) | A function on `&mut Map` |
| Valve | `if predicate(&data) { filter(&mut data)?; }` |
| Tap (`observe`) | The call, and its `Err` dropped: a failure does not stop the run |
| Nested pipeline | Its steps, in place |
| A setting of an instance (`self.rate`) | A `const`, from the literal that `DiscountFilter::new(0.1)` gives |
| `get`, `has`, `insert`, `remove`, `merge`, `to_dict` | Operations on the map |

| Refused | What to do |
|---|---|
| A Hook, or `observe(...)` on the pipeline | Run the pipeline itself |
| An `add_steps` that does more than add steps | Keep only the `add_*` calls |
| An argument that is not a literal | Give literal settings |
| A step that calls its own helper method or another impl | Put the code in the one method |
| `copy`, `with_trace`, `trace_id`, `lineage` | Run the pipeline itself |
| The Payload given to other code | Use it only through its operations |
| A step type from another crate | Compile steps whose source is in the project |

The fast mode only (no State, no Hooks), as in TypeScript. Python's
observable mode and inline layout come later, if the benchmark asks for them.

### The `rust:static` target

The TypeScript runner writes each case as a source file, compiles it and
imports it. Rust cannot load code while it runs, and a `cargo build` for each
case would take minutes. So the static target works in two stages: write
every case's pipeline as source, compile each into one generated crate (one
module for each case), build that crate once, and run it.

Done when: `rust:static` passes 11 cases and the 16 State and Hook cases as ✅\*,
as `typescript:static` does, and the refusal tests pass.

## Phase 4: the linter

Rust's types already check several rules:

| Rule | In Rust |
|---|---|
| `CUP-I004` a write outside a Filter | A type error (D2) |
| `CUP-A001`, `CUP-A002` a function as a step, `CUP-A008` a function as a Predicate | A type error (D5) |
| `CUP-A009` an object literal as a step | Not possible in Rust |

The rules that remain need a linter: `CUP-A003` (a step type declared inside
a function), `CUP-A005` (a plain nested `Pipeline`), `CUP-I003` (State read
by a step), `CUP-I005` (one primitive in each file), `CUP-I006` (the file
name), `CUP-I007` (the role suffix), `CUP-I008` (logic outside a primitive),
`CUP-I009` (a marker that allows nothing). `codeupipe-lint` for Rust is a
pipeline on `syn`, as the TypeScript linter is a pipeline on `typescript`.

This phase is last. The type system covers the rules that matter most for
correctness. The others are about form.

## Order and size

| Phase | What | Rough size |
|---|---|---|
| 0 | Settle D1 to D10 | One review of this page |
| 1 | Core crate, example, README | About 600 lines with tests (TypeScript: 415 lines of source) |
| 2 | Runner, `run.py`, bench, CI, documents | About 400 lines, most of it the JSON reader and the `cup_ops` |
| 3 | Compiler and `rust:static`, if the benchmark says so | About 1,000 lines (TypeScript: 851 lines of source) |
| 4 | Linter | About 1,200 lines |

Phases 1 and 2 are one release: `codeupipe` 0.1.0 for Rust, in the
conformance matrix. Phases 3 and 4 are later versions.
