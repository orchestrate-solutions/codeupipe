# codeupipe for Go

codeupipe is a library for writing a program as a pipeline of small steps.
This is the Go runtime. It has no dependencies.

It implements the same contract as the Python, TypeScript and Rust packages:
[conformance/API.md](../../conformance/API.md), and passes all its
conformance cases (`python conformance/run.py go:run`). There is no linter
and no compiler for Go yet ([docs/go-plan.md](../../docs/go-plan.md)).

The version is below 1.0: the package is not stable yet, and a new version
can change in a way that is not compatible.

No version is tagged yet. Use it from the main branch:

```bash
go get github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go@main
```

It needs Go 1.22 or later.

## The eight primitives

| Primitive | What it does | Who writes it |
|---|---|---|
| **Payload** | Carries the data | The library |
| **Filter** | Changes the data | You |
| **Predicate** | Asks a yes-or-no question about the data | You |
| **Valve** | Joins a Predicate to a Filter: the Filter runs when the answer is yes | The library. You add one with `AddValve(predicate, filter)` |
| **Tap** | Reads the data as it goes by | You |
| **Hook** | Is called before and after each step | You |
| **State** | Records which steps ran | The library |
| **Pipeline** | Runs the steps in order | You |

## Example

[examples/pricing/](examples/pricing/) has one type in each file. The
pipeline file adds them.

```go
// discount_filter.go
type DiscountFilter struct {
	Rate float64
}

func (f DiscountFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	price, _ := payload.Get("price").(float64)
	payload.Insert("price", math.Round(price*(1-f.Rate)*100)/100)
	return nil
}
```

```go
// at_least_predicate.go
type AtLeastPredicate struct {
	Key     string
	Minimum float64
}

func (q AtLeastPredicate) Test(ctx context.Context, payload *codeupipe.Payload) bool {
	value, _ := payload.Get(q.Key).(float64)
	return value >= q.Minimum
}
```

```go
// pricing_pipeline.go
type PricingPipeline struct{}

func (PricingPipeline) AddSteps(pipeline *codeupipe.Pipeline) {
	pipeline.AddFilter(DiscountFilter{Rate: 0.1})
	// MarkBulkFilter runs only when the predicate is true.
	pipeline.AddValve(AtLeastPredicate{Key: "qty", Minimum: 10}, MarkBulkFilter{})
	// A Tap only reads. If it fails, State records the error and the run goes on.
	pipeline.AddTap(AuditTap{})
}
```

```go
pipeline := codeupipe.NewNamedPipeline(PricingPipeline{})
result, err := pipeline.Run(ctx, codeupipe.NewPayload(map[string]any{"price": 100, "qty": 12}))
result.ToDict()
// map[bulk:true price:90 qty:12]
```

```bash
go run ./examples/pricing
```

## A payload of your own

`Payload` is the default, and it stays the default: a map of JSON-shaped
values that any developer can read, in any runtime of codeupipe. It shows
that anything can go there.

You can opt in to a type of your own, such as the struct that you would
write anyway. Give it a `Copy` method, and the steps of that pipeline take
the struct:

```go
type Order struct {
	Price float64
	Qty   float64
	Bulk  bool
}

func (o *Order) Copy() *Order {
	copied := *o
	return &copied
}

type MarkBulkFilter struct{}

func (MarkBulkFilter) Call(ctx context.Context, order *Order) error {
	order.Bulk = true
	return nil
}

pipeline := codeupipe.NewPipelineOf[*Order]()
pipeline.AddValve(BulkPredicate{}, MarkBulkFilter{})
```

Each primitive has a generic form, `FilterOf[P]`, `PredicateOf[P]`,
`TapOf[P]`, `HookOf[P]`, `NamedPipelineOf[P]` and `PipelineOf[P]`, and a
short name for the Payload: `Filter` is `FilterOf[*Payload]`, the same type.
Go has no default type parameter, so code for the Payload never writes `Of`.
The rules stay the same: `Run` works on a copy of the input, only a Filter
writes, a Tap failure is recorded and the run goes on, and the labels are the
same. A step for another type does not compile. Lineage is kept only if the
type also has `Stamp(label string)`.

## Names

The names are the names of the contract, in the case of Go.

| Contract | Go |
|---|---|
| `add_filter`, `add_valve`, `add_tap`, `add_pipeline`, `use_hook` | `AddFilter`, `AddValve`, `AddTap`, `AddPipeline`, `UseHook` |
| `run(p)`, `run(p, state)`, `state`, `labels` | `Run(ctx, p)`, `RunWithState(ctx, p, state)`, `State()`, `Labels()` |
| `observe(timing, lineage)` | `Observe(timing, lineage)`, two `bool`s |
| `get`, `has`, `insert`, `remove`, `merge`, `copy`, `to_dict`, `with_trace` | `Get`, `Has`, `Insert`, `Remove`, `Merge`, `Copy`, `ToDict`, `WithTrace` |
| `trace_id`, `lineage` | `TraceID()`, `Lineage()` |
| Hook: `before`, `after`, `on_error` | `Before`, `After`, `OnError` |
| construct | `NewPayload(map)`, `NewPipeline()`, `NewState()` |
| A named pipeline: `class PricingPipeline(Pipeline)` | A type with `AddSteps(pipeline *codeupipe.Pipeline)`, then `codeupipe.NewNamedPipeline(PricingPipeline{})` |

`Filter`, `Predicate`, `Tap` and `Hook` are interfaces. Embed
`codeupipe.HookBase` in a Hook, and write only the methods that you need.

## Differences from Python, TypeScript and Rust

- **`ctx` comes first.** Each step method and `Run` take a
  `context.Context`, as Go code that can wait does. The Pipeline gives it to
  each step and does nothing else with it: a cancelled `ctx` does not stop a
  run between steps. A step that calls the network or a database gives it
  the caller's `ctx`.
- **A value is an `any`**, in the shapes that `encoding/json` gives: `nil`,
  `bool`, `float64`, `string`, `[]any`, `map[string]any`. There is one number
  type: `Insert` and `NewPayload` keep an `int` (or any other Go number) as a
  `float64`, so `payload.Insert("qty", 12)` is read back with
  `.(float64)`. A list or a map is kept as it is given.
- **`Get` gives `nil` when a key is absent.** `Has` tells a key with a nil
  value from an absent key. A default is a type assertion:
  `price, ok := payload.Get("price").(float64)`.
- **The keys have no order**, as a Go map has none. `fmt` prints a map with
  its keys sorted.
- **A Filter changes the Payload in place** and returns `nil`, as the Payload
  is changed in place in TypeScript and Rust. A Hook's `OnError` sees the
  Payload as the failing step left it. A Tap, a Predicate and a Hook also get
  `*Payload`: Go has no pointer that only reads, so they must not write. As in
  Python and TypeScript, that is a rule for the linter, not for the compiler.
- **What the contract refuses when a step is added is a compile error.** A
  function is not a Filter, and `AddValve(filter, predicate)` does not
  compile. `refused_test.go` builds each shape and checks the error. A nil
  step compiles; it is refused with a panic when it is added.
- **`Run` is sync, and there is no `RunAsync`.** Go needs none: a step that
  waits blocks its goroutine. **A Pipeline can be run from many goroutines at
  the same time**, and each run writes into a State of its own. Add the steps
  before the first run.
- **`State()` is the State of the run that started last, once it has
  ended**, as in Rust. The run with the caller's State is
  `RunWithState(ctx, input, state)`.
- **A failure is an `error`.** `Run` returns the error of the step itself, so
  `errors.Is` and `errors.As` work, and `nil` for the data. A panic is not a
  failure: it is not caught, and a panicking Tap stops the run.
- **`Copy()` is shallow**, as the contract says: Go's maps and slices are
  references, so two Payloads share their values.
- **The label** is the name of the step's type, from `reflect`, without
  its package or type arguments. For a pointer it is the type that it points
  to. A struct type with no name gives `anonymous`.
- **The trace id** is `""` until it is set.

## Development

In this directory:

```bash
go test -race ./...
go vet ./...
gofmt -l .
go run ./examples/pricing
```

One primitive is in each file, and the file name is the type name in
snake_case. Each test is beside the file that it tests.

## License

Apache License 2.0.
