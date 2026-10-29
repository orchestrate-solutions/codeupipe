# codeupipe-compile for Rust

Writes a codeupipe pipeline in Rust as plain Rust: a struct with one field
for each key that the steps use, and one function for each step, with no
codeupipe. It reads the source and does not run it.

**The rule: code that compiles gives the same output as the pipeline. A
pipeline for which the compiler cannot keep that rule is refused, with the
place named.** A pipeline that compiles and then behaves in a different way
is a bug.

The compiler is a codeupipe pipeline:
[src/compile_pipeline.rs](src/compile_pipeline.rs). It depends on
`codeupipe`, on `syn` to read Rust, and on `prettyplease` to write it.

The version is below 1.0: the package is not stable yet. It is not on
crates.io. Build it from this repository:

```bash
cargo install --path packages/codeupipe-compile-rs
codeupipe-compile src/pricing PricingPipeline --out src/pricing_compiled.rs
```

The paths are the files (or directories) of the pipeline and its steps; the
last argument is the name of the pipeline type. With no `--out`, the module
goes to stdout. Exit code: **0** the module is written, **1** the pipeline
is refused (the message names the place and the fix), **2** the command
could not run. Nothing is written on 1 or 2.

From Rust: `codeupipe_compile::compile(&paths, "PricingPipeline")` returns
the text of the module, or the `Refusal`.

## Example

The pricing pipeline of [tests/fixtures/pricing/](tests/fixtures/pricing/)
compiles to [tests/expected/pricing.rs](tests/expected/pricing.rs):

```rust
pub struct PricingData {
    pub price: Option<f64>,
    pub qty: Option<f64>,
    pub bulk: Option<bool>,
}

fn cup_01_discount_filter(payload: &mut PricingData) -> Result<(), StepError> {
    let price = payload.price.unwrap_or(0.0) * (1.0 - 0.1);
    payload.price = Some(::core::convert::Into::into((price * 100.0).round() / 100.0));
    Ok(())
}

// ... one function for each step ...

pub fn run(input: &PricingData) -> Result<PricingData, StepError> {
    let mut payload = input.clone();
    cup_01_discount_filter(&mut payload)?;
    if cup_02_when_at_least_predicate(&payload) {
        cup_02_mark_bulk_filter(&mut payload)?;
    }
    let _ = cup_03_audit_tap(&payload);
    Ok(payload)
}
```

`run` takes the struct and returns a new one. The struct that the caller
gives is not changed. The body of each step is its own code, with each key
of the Payload as a field and each setting as its literal, so the Rust
compiler sees all of it.

## What compiles

| Shape | Plain form |
|---|---|
| `impl NamedPipeline for P` (of `Payload`) | `pub fn run(input: &PData)`. `add_steps` only adds steps (a `let` for a setting is allowed; the setting must still be a literal) |
| Filter (`call`) | A function on `&mut PData` |
| Valve | `if predicate(&payload) { filter(&mut payload)?; }` |
| Tap (`observe`) | `let _ = tap(&payload);`: a failure does not stop the run |
| A step made as `T`, `T { field: literal }` or `T::new(literal, ...)` | Each field of the step is a constant, from the literal. `new` may keep a parameter as it is, or with `.to_string()`, `.into()`, `.to_owned()` or `String::from(..)` |
| `payload.get(K).and_then(Value::as_f64)` (or `as_bool`, `as_str`, or a closure `\|v\| v.as_f64()`) | `payload.k` (`payload.k.as_deref()` for text) |
| `payload.has(K)` | `payload.k.is_some()` |
| `payload.insert(K, v)` | `payload.k = Some(v.into())` |
| `payload.remove(K)` | `payload.k = None` |
| The arguments of `format!`, `println!` and other macros | Read and rewritten as code |
| `use` items of a step file that are not of codeupipe or of the project | The same `use`, in the module |

A key `K` is text in the code: a literal, or a setting that the pipeline
gives as text. Its field has the name of the key; a character that a Rust
name cannot have becomes `_`.

**The type of a key** comes from the reads and the writes that show one:
`as_f64` or a number is `f64`, `as_bool` or `true`/`false` is `bool`,
`as_str`, text, `format!`, `String::from` or `.to_string()` is `String`. A
key that the steps only test (`has`) or remove is text. Each field is an
`Option`, because a Payload can lack a key.

## What is refused

| Shape | What to do |
|---|---|
| A Hook, or `observe(...)` on the pipeline | The compiled code has no lifecycle and no State. Run the pipeline itself |
| A nested pipeline (`add_pipeline`) | Not compiled yet. Add its steps to this pipeline |
| A pipeline of a type of your own (`NamedPipeline<Order>`) | It is plain data already |
| A setting that is not a literal, or that the constructor computes | Give each setting as a literal, and compute in the method of the step |
| A key that is not text in the code | Write the key, or give it as a setting |
| A key with two types | Give each key one type |
| A key whose type no use shows (only written with an expression) | Read it once with `.and_then(Value::as_...)`, or write a literal |
| `payload.get(K)` with no `.and_then(Value::as_...)` | Read the key with its type |
| Another method of the Payload (`to_dict`, `copy`, `merge`...), or the Payload given to other code | Use the Payload only through get, has, insert and remove |
| A chain of writes (`payload.insert(..).insert(..)`) | Write one key in each statement |
| `self.method()`, or `self` used in another way | Put the code of the step in its method |
| A `Value` used in another way | Read the key with its type |
| A step with no source in the paths | Give the file of each step |

The tests for each refusal are in [tests/compile.rs](tests/compile.rs). The
runtime's own pricing example is refused, because its Tap prints
`payload.to_dict()`, which plain data has not:

```
../codeupipe-rs/examples/pricing/audit_tap.rs:9:33  `payload.to_dict()` is not in plain data. Use the Payload only through get(..).and_then(Value::as_...), has, insert and remove
```

## What the compiled code does not have

- **State.** No `executed`, `skipped`, `errors` or `timings`.
- **Hooks.** A pipeline with a Hook is refused.
- **Tap errors.** They are contained, as in the pipeline, but not recorded.
- **Labels.** A function has a name such as `cup_01_discount_filter`.
- **A Payload.** The caller gives and gets the struct.

## How fast

`cargo run --release --example bench` (Apple M1, best of 9 × 20,000, the
two alternated):

| Pipeline | `Pipeline::run` | Compiled | |
|---|---|---|---|
| pricing: 3 steps of arithmetic | 0.237 µs | 0.0016 µs | 150x |
| signup: 4 steps of text (trim, lower case, format) | 0.504 µs | 0.164 µs | 3.1x |

The more a step does, the less the pipeline costs next to it: with steps
of real work the gain is small. The large gain is for many runs of light
steps.

## How it is checked

- [tests/same_output.rs](tests/same_output.rs): the modules of
  [tests/expected/](tests/expected/) are compiled into the test and give
  the output and the errors of the pipelines that they come from, on many
  inputs, and do not change their input.
- [tests/compile.rs](tests/compile.rs): the compiler writes those modules
  (the code is compared, not its layout; `UPDATE_EXPECTED=1` writes them
  again), and refuses each shape above with its place.

## Not yet

- A conformance target `rust:static`, judged by the cases of
  `conformance/cases/` as `typescript:static` is.
- Nested pipelines.
- A `from_map`/`to_map` for a caller that has a Payload.

## Development

A Cargo workspace of its own, as the linter. In this directory:

```bash
cargo test
cargo clippy --all-targets -- -D warnings
cargo run --release --example bench
```

## License

Apache License 2.0.
