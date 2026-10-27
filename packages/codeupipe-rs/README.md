# codeupipe for Rust

codeupipe is a library for writing a program as a pipeline of small steps.
This is the Rust runtime. It has no dependencies.

It implements the same contract as the Python and TypeScript packages:
[conformance/API.md](../../conformance/API.md). The conformance runner for
Rust is not written yet ([docs/rust-plan.md](../../docs/rust-plan.md), phase 2).

The version is below 1.0: the package is not stable yet, and a new version
can change in a way that is not compatible.

The crate is not on crates.io yet. Use it from this repository:

```toml
[dependencies]
codeupipe = { git = "https://github.com/orchestrate-solutions/codeupipe", branch = "beta" }
```

## The eight primitives

| Primitive | What it does | Who writes it |
|---|---|---|
| **Payload** | Carries the data | The library |
| **Filter** | Changes the data | You |
| **Predicate** | Asks a yes-or-no question about the data | You |
| **Valve** | Joins a Predicate to a Filter: the Filter runs when the answer is yes | The library. You add one with `add_valve(predicate, filter)` |
| **Tap** | Reads the data as it goes by | You |
| **Hook** | Is called before and after each step | You |
| **State** | Records which steps ran | The library |
| **Pipeline** | Runs the steps in order | You |

## Example

[examples/pricing/](examples/pricing/) has one type in each file. The
pipeline file adds them.

```rust
// discount_filter.rs
use codeupipe::{Filter, Payload, StepError, Value};

pub struct DiscountFilter {
    rate: f64,
}

impl Filter for DiscountFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let price = payload.get("price").and_then(Value::as_f64).unwrap_or(0.0) * (1.0 - self.rate);
        payload.insert("price", (price * 100.0).round() / 100.0);
        Ok(())
    }
}
```

```rust
// at_least_predicate.rs
use codeupipe::{Payload, Predicate, Value};

pub struct AtLeastPredicate {
    key: String,
    minimum: f64,
}

impl Predicate for AtLeastPredicate {
    fn test(&self, payload: &Payload) -> bool {
        payload.get(&self.key).and_then(Value::as_f64).unwrap_or(0.0) >= self.minimum
    }
}
```

```rust
// pricing_pipeline.rs
use codeupipe::{NamedPipeline, Pipeline};

pub struct PricingPipeline;

impl NamedPipeline for PricingPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_filter(DiscountFilter::new(0.1));
        // MarkBulkFilter runs only when the predicate is true.
        pipeline.add_valve(AtLeastPredicate::new("qty", 10.0), MarkBulkFilter);
        // A Tap failure is recorded and does not stop the run.
        pipeline.add_tap(AuditTap);
    }
}
```

```rust
use codeupipe::{Map, Payload, Pipeline};

let mut pipeline = Pipeline::named(PricingPipeline);
let result = pipeline.run(&Payload::from_map(Map::from([("price", 100.0), ("qty", 12.0)])))?;
result.to_dict();
// {"price": 90, "qty": 12, "bulk": true}
```

```bash
cargo run --example pricing
```

## Names

The names are the names of the contract.

| Contract | Rust |
|---|---|
| `add_filter`, `add_valve`, `add_tap`, `add_pipeline`, `use_hook` | the same |
| `run`, `state`, `labels` | `run`, `state()`, `labels()` |
| `observe(timing, lineage)` | `observe(timing, lineage)`, two `bool`s |
| `get`, `has`, `insert`, `remove`, `merge`, `copy`, `to_dict`, `with_trace` | the same |
| `trace_id`, `lineage` | `trace_id()`, `lineage()` |
| Hook: `before`, `after`, `on_error` | the same |
| A named pipeline: `class PricingPipeline(Pipeline)` | `impl NamedPipeline for PricingPipeline`, then `Pipeline::named(PricingPipeline)` |

`Filter`, `Predicate`, `Tap` and `Hook` are traits. The methods of `Hook` do
nothing unless you implement them.

## Differences from Python and TypeScript

- **A Filter gets `&mut Payload`.** It writes in place, as the Payload is
  changed in place in TypeScript, and returns `Ok(())`. A Tap, a Predicate and
  a Hook get `&Payload`, so **only a Filter can write, and the compiler checks
  it**. A Hook's `on_error` sees the Payload as the failing step left it.
- **What the contract refuses when a step is added is a compile error.** A
  closure is not a Filter, and `add_valve(filter, predicate)` does not
  type-check. The doc tests in `src/lib.rs` check this.
- **`get` gives `Option<&Value>`.** Absent is `None`. A default is
  `.unwrap_or(...)`. `Value` is JSON-shaped, with one number type: `1` and
  `1.0` are the same value.
- **`run` is sync, and there is no `run_async` yet.** It takes `&mut self`,
  so two runs of one pipeline at the same time are not possible.
- **A failure is an `Err`.** A panic is not a failure: it is not caught, and
  a panicking Tap stops the run.
- **`copy()` is deep.** A value shared by two Payloads could not be changed in
  place anyway, so the behaviour is the same as the shallow copy of the
  contract.
- **The label** is the type name without its path or generic arguments. It
  comes from `std::any::type_name`, whose exact text Rust does not promise to
  keep the same; the tests check it.
- **Timing in WebAssembly.** `std::time::Instant` panics on
  `wasm32-unknown-unknown`. Timing is off by default, so a pipeline runs
  there as long as `observe(true, ...)` is not called.

## Development

The Rust packages are one Cargo workspace. At the root of the repository:

```bash
cargo test                   # the tests, and the doc tests
cargo clippy -- -D warnings
cargo fmt --check
cargo run --example pricing
```

One primitive is in each file, and the file name is the type name in
snake_case.

## License

Apache License 2.0.
