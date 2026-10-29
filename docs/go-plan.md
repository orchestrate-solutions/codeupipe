# Plan: codeupipe for Go

This is a plan, not a reference. It says how the fourth runtime is added: a
Go runtime with the same contract ([conformance/API.md](../conformance/API.md)),
judged by the same conformance cases, in the same layout as TypeScript and
Rust.

**How it is built: from the contract, tests first.** Each behaviour starts as
a failing test that comes from a rule of the contract or from a test of the
TypeScript package. **When in doubt, do what the TypeScript package does**: it
is the reference for every question that the contract does not answer. Where
Rust already answered a question that Go also raises, the Rust answer is the
start ([rust-plan.md](rust-plan.md)).

The Go runtime in the old repository (`runtimes/go`) is not the start. Its
API is from before version 2: steps named by hand, a Payload that does not
change, no Predicate, and a dependency (`msgpack`). It can be read for ideas.
No code is copied from it.

## What Go gives for free

- **A JSON value.** `encoding/json` reads JSON into `any`: `nil`, `bool`,
  `float64`, `string`, `[]any`, `map[string]any`. That is the contract's value
  (D1). Rust had to write its own `Value` and its own JSON reader. Go needs
  neither, in the runtime or in the conformance runner.
- **A reader and a writer of Go.** `go/parser`, `go/ast`, `go/types` and
  `go/format` are in the standard library. The compiler (phase 3) and the
  linter (phase 4) need no dependency. Rust needs `syn`, TypeScript needs
  `typescript`.
- **Labels.** An interface value keeps the type of the step, so
  `reflect.TypeOf` gives its name when the step is added. The Rust runner
  needed a trick (`UseFilter`) to keep the type of a step it picks at run
  time. The Go runner does not.

## Versions

The Go module starts at **0.1.0**, as TypeScript and Rust did. A version
below 1.0 is not stable yet.

Go has no registry to publish to: a tag on a public repository is a release.
For a module in a subdirectory, the tag has the directory in its name:
`packages/codeupipe-go/v0.1.0`. **No tag is made until it is decided**, as each
Rust crate has `publish = false`. Until then a project uses the main branch:

```bash
go get github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go@main
```

## Layout

| Path | Module or package | Contents | Phase |
|---|---|---|---|
| `packages/codeupipe-go/` | package `codeupipe` | The eight primitives. No dependencies | 1 |
| `conformance/runners/go/` | (a command, not published) | The conformance runner, with its `cup_ops` steps | 2 |
| `packages/codeupipe-compile-go/` | `codeupipe-compile` | Writes a pipeline as plain Go | 3 |
| `packages/codeupipe-lint-go/` | `codeupipe-lint` | The linter for the rules that the types do not check | 4 |

One primitive is in each file, and the file name is the type name in
snake_case, as in Python and Rust: `DiscountFilter` is in
`discount_filter.go`. Go keeps a test beside its source, so the repository's
rule "tests mirror source" is the language's own: `payload.go` and
`payload_test.go`.

### The core package

```
packages/codeupipe-go/
  go.mod                module github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go
  README.md  LICENSE  NOTICE
  payload.go            Payload
  filter.go             FilterOf[P], and Filter for a Payload
  predicate.go          PredicateOf[P], and Predicate
  tap.go                TapOf[P], and Tap
  hook.go               HookOf[P], and Hook
  state.go              State
  valve.go              valve (not a public name)
  pipeline.go           PipelineOf[P], and Pipeline
  pipeline_data.go      PipelineData[P]: the one thing a type of your own needs
  named_pipeline.go     NamedPipeline (see D7)
  step_label.go         the label from the type name
  *_test.go             one beside each file that it tests
  examples/pricing/
    main.go  discount_filter.go  mark_bulk_filter.go  at_least_predicate.go
    audit_tap.go  print_steps_hook.go  pricing_pipeline.go
```

## Decisions

These are the questions that Go raises. **They are settled as recommended**
(2026-10-29), with `ctx` on every step (D4).

### D1. Values

**The question.** Values are JSON-shaped, and the core has no dependencies.

**Recommendation.** A value is an `any` in the shapes that `encoding/json`
gives: `nil`, `bool`, `float64`, `string`, `[]any`, `map[string]any`. There is
no `Value` type of codeupipe. One number type, `float64`, as JSON, JavaScript
and the Rust runtime have, and as the judge compares (`1 == 1.0`).

`Insert` changes Go's other number types (`int`, `int64`, `float32` and the
others) to `float64`. Without that, `payload.Insert("qty", 12)` would be read
back by `payload.Get("qty").(float64)` as "not a number", with no error. The
change is a type switch on the value, so it costs almost nothing. It is done at
the top of the value only: a list or a map is kept as it is given. The runtime
does not check other shapes (a struct, a `[]int`). The linter can (phase 4).

The keys have no order, as a Go map has none. Rust kept the order in which
keys were added, for people; the judge does not compare order. `fmt` prints a
map with its keys sorted, so a printed Payload is still the same each time.

### D2. `get` with a default

**The question.** The contract has `get(k, default)`. Go has no default
arguments and no overloads.

**Recommendation.** `Get(key string) any`, which gives `nil` when the key is
absent. `nil` is Go's null, and the contract says that absent is the
language's null. `Has` tells a key with a null value from an absent key.

A default is Go's own way, a type assertion that gives a zero value:

```go
price, _ := payload.Get("price").(float64) // 0 when absent, null or not a number
qty, ok := payload.Get("qty").(float64)
if !ok {
	qty = 1
}
```

This is what Rust did with `.unwrap_or(...)`: the language's way, not a second
name. The other choice is `Get(key string, fallback ...any) any`, which is
nearer to Python and TypeScript, but lets `Get("a", 1, 2)` compile.

### D3. A write, and what a step gets

**The question.** The contract says that a write changes the Payload and
returns it.

**Recommendation.** As TypeScript and Rust: a Filter changes the Payload in
place, and a write returns it, so writes chain.

```go
func (f DiscountFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	price, _ := payload.Get("price").(float64)
	payload.Insert("price", math.Round(price*(1-f.Rate)*100)/100)
	return nil
}
```

When a Filter fails, `OnError` gets the same Payload, with the writes that the
Filter made before it failed. That is what TypeScript does.

A Tap, a Predicate and a Hook also get `*Payload`. Go has no pointer that only
reads, so **a write outside a Filter is not a type error, as it is in Rust**.
It is the linter's rule `CUP-I004`, as in Python and TypeScript. An interface
that only reads was looked at and is not recommended: it cannot cover a type
of your own (D9), and each read would be a call through an interface.

### D4. `context.Context`

**The question.** In Go, a function that can wait (on the network, a file, a
database) takes a `context.Context` first, for cancellation and deadlines. The
contract has no cancellation. **This is the decision that changes how every
step looks**, so it is made now: to add it later changes every step.

**Recommendation.** Every method of a step takes `ctx` first, and `Run` takes
it too: `Call(ctx, payload)`, `Test(ctx, payload)`, `Observe(ctx, payload)`,
`Before(ctx, step, payload)`, `Run(ctx, input)`. **The Pipeline gives `ctx` to
each step and does nothing else with it**: it does not stop between steps when
`ctx` is cancelled. So the contract does not change. A step that calls
`http.NewRequestWithContext` or `db.QueryContext` gives it the caller's `ctx`,
which is what a Go reviewer looks for.

Stopping a run between steps when `ctx` is cancelled would be a new rule. It
enters the contract with a conformance case, if a real pipeline needs it.

The other choice is no `ctx` in 0.1.0 (principle 5: nothing that is not in the
contract). Then a step that needs one has no way to get the caller's, and uses
`context.Background()`.

### D5. Errors and panics

**Recommendation.** As Rust. A step returns `error`. `Run` returns that same
error, so `errors.Is` and `errors.As` work on it. `OnError` gets it, and
`State.Errors` keeps the label and the error.

**A panic is not a failure of a step** and is not caught: a panicking Tap
stops the run. The README says so. Catching a panic with `recover` can be added
later with no change to the API.

### D6. Labels

**Recommendation.** `reflect.TypeOf` of the step when it is added. For a
pointer, the type that it points to. Type arguments are dropped
(`Wrapper[pkg.Inner]` gives `Wrapper`). A type with no name (a struct literal
that embeds a step) gives `anonymous`, as in TypeScript. Checked on Go 1.25
with a `go 1.22` module:

| Step | `reflect` name | Label |
|---|---|---|
| `DiscountFilter{}` | `DiscountFilter` | `DiscountFilter` |
| `&DiscountFilter{}` | (pointer) | `DiscountFilter` |
| `Wrapper[DiscountFilter]{}` | `Wrapper[main.DiscountFilter]` | `Wrapper` |
| `struct{ DiscountFilter }{}` | `` | `anonymous` |

What the contract refuses with a `TypeError` is a compile error in Go: a value
with no `Call` does not implement the Filter interface, and
`AddValve(filter, predicate)` does not compile, since a Filter has no `Test`.

A plain function is not a step, since it has no `Call` method. But Go lets a
function type have a method (`type FilterFunc func(...) error`, as
`http.HandlerFunc`). **The runtime gives no such adapter.** A user that writes
one gets the label `FilterFunc`; the linter flags it (`CUP-A001`).

### D7. A named pipeline

**Recommendation.** As Rust: an interface with one method that adds the steps.
The label is the name of the type.

```go
type PricingPipeline struct{}

func (PricingPipeline) AddSteps(pipeline *codeupipe.Pipeline) {
	pipeline.AddFilter(DiscountFilter{Rate: 0.1})
	// MarkBulkFilter runs only when the predicate is true.
	pipeline.AddValve(AtLeastPredicate{Key: "qty", Min: 10}, MarkBulkFilter{})
	// A Tap only reads. If it fails, State records the error and the run goes on.
	pipeline.AddTap(AuditTap{})
}

pipeline := codeupipe.NewNamedPipeline(PricingPipeline{})
```

`AddSteps` is also what the compiler reads (phase 3). A plain
`codeupipe.NewPipeline()` has the label `Pipeline`.

### D8. Run, State, and goroutines

**Recommendation.** `Run(ctx, input) (*Payload, error)` is sync, which is all
that Go needs: a step that waits blocks its goroutine, and a caller that wants
runs at the same time starts goroutines. Go has no async functions, so there is
no `RunAsync` and no `AsyncStepInSyncRun`. Principle 3 holds by itself.

Goroutines really do run at the same time, so "a State belongs to one run" is
not only for overlap inside one thread, as it is in JavaScript.

- `RunWithState(ctx, input, state)` is the run with the caller's State (Go
  has no optional argument; the name is Rust's).
- `pipeline.State()` is the State of the run that started last, once it has
  ended (Rust's rule). Each run takes a number from an atomic counter when it
  starts, and its State is kept at the end only if no later run has started.
- **A Pipeline can be run from many goroutines at the same time.** Adding a
  step while it runs is not supported; the README says so.
- The tests run with `go test -race`, in CI too.

Rust keeps the storage of a State between runs for speed. Go does that only if
the benchmark shows a need.

### D9. A type of your own

**The question.** The contract lets a pipeline carry a type of your own in
place of the Payload. Go has generics (1.18), but **no default type
parameter**, so Rust's `Pipeline<P = Payload>` has no Go form.

**Recommendation.** Each primitive has a generic form, `...Of[P]`, and an
alias for the Payload with the short name. The alias is the same type, not a
second one, so principle 1 holds.

```go
type FilterOf[P any] interface {
	Call(ctx context.Context, payload P) error
}

type Filter = FilterOf[*Payload]
type Pipeline = PipelineOf[*Payload]
```

Code for the Payload never writes `Of`. A type of your own:

```go
pipeline := codeupipe.NewPipelineOf[*Order]()
pipeline.AddFilter(DiscountOrderFilter{}) // a FilterOf[*Order]
```

`P` must have `Copy() P`, for the copy that `run` works on (`PipelineData[P]`).
Lineage is kept only by a type that also has `Stamp(label string)`. A step for
one type in a pipeline of another does not compile.

The alias of an instantiated generic type is checked on Go 1.25 with a
`go 1.22` module.

### D10. The Go version

**Recommendation.** `go 1.22` in `go.mod`. Generics need 1.18. From 1.22, each
iteration of a loop has its own variable, which removes a class of goroutine
bugs in the code of the user. CI tests 1.22 and the newest Go. This machine has
1.25.

### D11. Names

**Recommendation.** The module is
`github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go`, and the
package is `codeupipe`, so the code reads `codeupipe.Payload`. A user who wants
it short imports it as `cup`. The directory and the package have different
names, which Go allows (`gopkg.in/yaml.v3` is the package `yaml`).

The names are Go's: `AddFilter`, `AddValve`, `AddTap`, `AddPipeline`,
`UseHook`, `Run`, `RunWithState`, `State`, `Labels`, `Observe`, `Insert`,
`Remove`, `Merge`, `Copy`, `ToDict`, `WithTrace`, `TraceID`, `Lineage`,
`OnError`. A constructor is `New...`: `NewPayload(map)`, `NewPipeline()`,
`NewNamedPipeline(p)`, `NewState()`.

### D12. Copy

**Recommendation.** As the contract and TypeScript: `Copy()` is shallow, and
`NewPayload(map)` copies the map that it is given, not the values in it. Go's
maps and slices are references, so this is exactly "the two payloads have
separate keys and share their values". Rust had to make a deep copy; Go does
not.

## Phase 1: the core package

**Done** (2026-10-29): `packages/codeupipe-go`, 725 lines of source with
their doc comments, and 60 tests in 1,001 lines (18 Payload, 23 Pipeline, 9
labels, 6 a type of your own, 1 of what does not compile, 3 the example). `go test -race`, `go vet`,
`gofmt` and `staticcheck` are clean on Go 1.22.12 and 1.25.0. The tests are
ported from `packages/codeupipe-ts/tests`, except the async ones, which have
no Go form, and add what only Go has: `ctx` reaches each step, a cancelled
`ctx` does not stop a run, 50 runs in goroutines at the same time, and a nil
step refused when it is added. To check that the tests catch a broken
runtime, two rules were broken on purpose: keeping the State of a run that
did not start last failed 1 test, and not recording a Tap failure failed 2.

What the contract refuses when a step is added is a compile error, and
`refused_test.go` checks it as Rust's `compile_fail` tests do: it builds six
small programs (a function as a step, a Filter as a Tap, `AddValve` in the
wrong order, a step for another type, a run of another type, a type with no
`Copy`) and checks that each build fails with the error that names the cause.
A seventh program with the right steps must compile, so that a failure comes
from the shape.

The eight primitives, to the contract, with the decisions above.

1. `payload.go`, tests first (RED, GREEN, REFACTOR), from the Payload table
   of the contract and `packages/codeupipe-ts/tests`.
2. The interfaces: `FilterOf`, `PredicateOf`, `TapOf`, `HookOf`.
   `step_label.go`.
3. `State`, the valve, `PipelineOf` (`AddFilter`, `AddValve`, `AddTap`,
   `AddPipeline`, `UseHook`, `Run`, `RunWithState`, `State`, `Labels`,
   `Observe`), and `NamedPipeline`.
4. The pricing example, with its test, giving
   `{"price": 90, "qty": 12, "bulk": true}`.
5. The README, in the form of the TypeScript and Rust READMEs.

Done when: `go test -race ./...`, `go vet ./...` and `gofmt -l .` (no output)
pass on Go 1.22 and on the newest Go, and `go run ./examples/pricing` prints
the result and the State.

## Phase 2: conformance

**Done** (2026-10-29): `go:run` passes all 30 cases, with nothing
unsupported, and every other target still passes in the same run of
`run.py`. To check that the runner catches a broken runtime, three rules were
broken on purpose: not recording a Tap failure failed 4 cases, keeping the
State of a run that did not start last failed 1, and not sending `OnError`
for the pipeline failed 2. The runner is 523 lines (`main.go`, `bench.go`)
and 19 files in `cup_ops/` (402 lines), with `encoding/json` and no JSON
reader of its own. The judge has a `GoProbe` and `run.py` leaves `go:run`
out on a machine with no `go`; `bench.py` keeps its baseline under `go`; CI
has a `go` job (gofmt, vet, staticcheck, `go test -race`, the example,
`go:run`, and Go 1.22); and API.md has a Go column and notes.

The first numbers showed a 10-step run at 0.69 µs. A Go benchmark of 10
no-op steps showed 9 allocations a run, 4 of them the list of executed
labels in State, which grew at each step. It is now made once with room for
every step: 10 no-op steps went from 356 to 217 ns. What is left is mostly
the number that each `add` writes: an `any` holds a `float64` in an
allocation of its own (D1).

µs per run, Apple Silicon, one run of `python conformance/bench.py`:

| scenario | python:run | python:static-inline | rust:run | go:run |
|---|---|---|---|---|
| `micro-pass` (10 filters) | 4.79 | 0.627 | 0.276 | 0.546 |
| `valve-gated` | 5.14 | 0.860 | 0.326 | 0.612 |
| `taps` | 5.03 | 0.626 | 0.293 | 0.567 |
| `hook` | 5.41 | — | 0.286 | 0.626 |
| `heavy-allocation` (50 inserts) | 15.03 | 1.51 | 4.40 | 2.15 |

The dynamic Go run is 9 times faster than `python:run`, about as fast as
compiled Python, and half as fast as Rust, except where a run makes 50 new
keys: there Go's map is twice as fast as the Rust runtime's.

What follows is the plan as it was written.

A runner in `conformance/runners/go/`, with the protocol of the others:
`runner <target> < cases.json > results.json`. It never judges.

- **Steps.** `cup_ops/` has one file for each step type, with the names of the
  TypeScript and Rust runners: `SetFilter`, `CopyFilter`, `AddFilter`,
  `AppendFilter`, `RemoveFilter`, `MergeFilter`, `HasFilter`, `MutateFilter`,
  `FailFilter`, `RunAgainFilter`, `RecordTap`, `FailTap`, `NoopTap`,
  `EqualsPredicate`, `TruthyPredicate`, `RecordHook`, `NoopHook`,
  `NestedPipeline`.
- **JSON.** `encoding/json`. No reader of its own.
- **Offline.** Its own `go.mod`, with a `replace` to the package. `run.py`
  runs it with `GOFLAGS=-mod=mod GOPROXY=off`, so it cannot download. With no
  `go` on the machine, `run.py` leaves the target out, as it does for `cargo`.
- **`equals` and `truthy`** (open questions 3 and 4 of the conformance
  README): as Rust. `equals` compares by content, and a number is never equal
  to a bool. `truthy` follows Python: an empty list or map is false.
- **Benchmark.** `go:run` in `bench.py`, with a reference of map writes of its
  own, as Rust has.
- **CI.** A `go` job: `gofmt`, `go vet`, `go test -race`, the example,
  `python conformance/run.py go:run`, and the tests again on Go 1.22.
- **Documents.** A Go column in the "Runtimes" table of API.md, a row in the
  README's table of packages, and `go:run` in MATRIX.md.

Done when: `go:run` passes all 30 cases, with nothing unsupported. To check
that the runner catches a broken runtime, the runtime is broken on purpose
(a Tap failure not recorded) and cases must fail.

Phases 1 and 2 are one release: `codeupipe` 0.1.0 for Go, in the conformance
matrix.

## Phase 3: compile, and phase 4: the linter

Later versions, each with a plan of its own when it starts. Both use only the
standard library (`go/parser`, `go/ast`, `go/types`, `go/format`). The compiler
starts only after phase 2 measures `go:run`, as the Rust compiler waited for
`rust:run`: it is worth writing only if the number leaves room for a gain.

## Order and size

| Phase | What | Rough size |
|---|---|---|
| 0 | Settle D1 to D12. **Done** (2026-10-29) | One review of this page |
| 1 | Core package, example, README | About 500 lines of source and 600 of tests (TypeScript: 450 lines of source) |
| 2 | Runner, `run.py`, bench, CI, documents | About 300 lines: no JSON reader to write |
| 3 | Compiler | Later |
| 4 | Linter | Later |
