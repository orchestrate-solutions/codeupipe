# codeupipe-core — Rust

Rust runtime of the codeupipe core pipeline primitives. Zero external dependencies. WASM-compatible.

All runtimes share the same 8 primitives. Each is a first-class citizen optimized for its domain: **Rust** for WASM + desktop + embedded, **TypeScript** for web + browser, **Python** for prototypes + backend, **Go** for cloud, **C#** for .NET + games.

## Quick Start

```rust
use codeupipe_core::{Payload, Pipeline, Filter, Value};

struct Greet;
impl Filter for Greet {
    fn call(&self, payload: Payload) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
        let name = payload.get("name").and_then(|v| v.as_str()).unwrap_or("World");
        Ok(payload.insert("greeting", Value::Str(format!("Hello, {}!", name))))
    }
}

fn main() {
    let mut pipeline = Pipeline::new().add_filter(Greet);

    let result = pipeline.run(
        Payload::new().insert("name", Value::Str("World".to_string()))
    ).unwrap();

    println!("{}", result.get("greeting").unwrap().as_str().unwrap());
    // "Hello, World!"
    println!("{:?}", pipeline.state().executed); // ["my_crate::Greet"]
}
```

## Step identity

Steps have no names. Each is identified by its filter's type path,
`std::any::type_name` captured where it is added (`my_crate::Greet`, `#2`
from the second use), which State and Hooks report (conformance/API.md,
"Step identity"). `add_*` are generic over the concrete type:

- `add_filter(Greet)`, not `add_filter(Box::new(Greet), "greet")`. A
  `Box<dyn Filter>` does not implement `Filter` (a compile error): its type,
  and so its identity, is gone.
- **Valve predicates**: objects, a named type implementing `Predicate`,
  configuration in its fields (`Valve::new(Discount, AtLeast(100))`). There
  is no impl for fns or closures, so passing one does not compile.
- **Nested pipelines**: a named type implementing `Nestable`
  (`struct Onboarding(Pipeline)`). `Pipeline` does not implement it, so
  nesting a plain pipeline is a compile error.
- **Parallel groups**: `add_parallel(Parallel::new().with(A).with(B))`.
- A struct declared **inside a function** has an ordinary-looking path; the
  linter catches that one.
- `type_name` is best-effort across compiler versions: pin the toolchain,
  since an upgrade can change identities.

## Core Types

| Type | Role |
|------|------|
| `Payload` | Immutable data container |
| `MutablePayload` | Mutable sibling for bulk edits |
| `Value` | Dynamic value enum (Int, Float, Str, Bool, List, Map, Null) |
| `Filter` | Processing trait — `call(payload) → Result<Payload>` |
| `StreamFilter` | Streaming trait — `stream(chunk) → Vec<Payload>` |
| `Pipeline` | Orchestrator — `.run()` / `.stream()` |
| `Valve` | Conditional gate — filter + predicate |
| `Tap` | Read-only observer — `.observe(&payload)` |
| `State` | Execution metadata |
| `Hook` | Lifecycle — before / after / on_error |

## Tests

```bash
cargo test          # Run all tests
cargo test -- -v    # Verbose output
```

## WASM

The crate has no external dependencies and avoids platform-specific APIs,
making it compatible with `wasm32-unknown-unknown` targets:

```bash
cargo build --target wasm32-unknown-unknown
```
