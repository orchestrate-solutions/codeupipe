# codeupipe-core (Go)

Go runtime of codeupipe's 8 core pipeline primitives. Zero external dependencies — stdlib only.

All runtimes share the same 8 primitives. Each is a first-class citizen optimized for its domain: **Go** for cloud infrastructure + concurrent services, **TypeScript** for web + browser, **Python** for prototypes + backend, **Rust** for WASM + desktop, **C#** for .NET + games.

## Quick Start

```go
package main

import (
    "fmt"
    cup "github.com/codeuchain/codeupipe-core/codeupipe"
)

// A simple filter that doubles a number.
type DoubleFilter struct{}

func (f *DoubleFilter) Call(p cup.Payload) (cup.Payload, error) {
    n, _ := p.Get("n").(float64)
    return p.Insert("n", n*2), nil
}

func main() {
    pipeline := cup.NewPipeline().AddFilter(&DoubleFilter{})

    result, err := pipeline.Run(cup.NewPayload(map[string]any{"n": float64(5)}))
    if err != nil {
        panic(err)
    }
    fmt.Println(result.Get("n"))             // 10
    fmt.Println(pipeline.State().Executed)   // [example.com/app.DoubleFilter]
}
```

## Step identity

Steps have no names. Each is identified by its filter's fully qualified
symbol, derived with `reflect` (`example.com/app.DoubleFilter`, `#2` from the
second use), which State, Hooks and events report (conformance/API.md,
"Step identity"). It survives stripped, `-trimpath` release builds.

- **Filters, taps**: named types. An anonymous struct panics with
  `*AnonymousStep` when added.
- **Func adapters** (`type F func(Payload) (Payload, error)`): identified by
  the wrapped function; a func literal or closure panics.
- **Valve predicates**: objects, a named type implementing `Predicate`
  (`Test(Payload) bool`), configuration in its fields
  (`cup.NewValve(f, atLeast{10})`). A plain function does not compile; a
  func adapter type is identified by the function it wraps, so a closure
  still panics.
- **Nested pipelines**: a named type embedding `*Pipeline`
  (`type Onboarding struct{ *cup.Pipeline }`, passed as `AddPipeline(Onboarding{p})`).
  A plain `*Pipeline` panics.
- A type declared **inside a function** looks like a package-level type to
  `reflect`, so the runtime cannot refuse it; the linter does.

## Core Types

| Type | File | Role |
|------|------|------|
| `Payload` | payload.go | Immutable data container |
| `MutablePayload` | payload.go | Mutable sibling for bulk edits |
| `Filter` | filter.go | Processing interface — `Call(payload) (Payload, error)` |
| `StreamFilter` | stream_filter.go | Streaming — `Stream(chunk) ([]Payload, error)` |
| `Pipeline` | pipeline.go | Orchestrator — `.Run()` / `.Stream()` |
| `Valve` | valve.go | Conditional gate — filter + predicate |
| `Tap` | tap.go | Read-only observer — `.Observe(payload)` |
| `State` | state.go | Execution metadata |
| `Hook` | hook.go | Lifecycle — `Before` / `After` / `OnError` |
| `DefaultHook` | hook.go | No-op Hook for embedding |

## Go-Idiomatic Design

- **Interfaces** for Filter, StreamFilter, Tap, Hook (duck-typed)
- **Goroutines** for `AddParallel()` — real concurrency via `sync.WaitGroup`
- **Channels** for `Stream()` — idiomatic Go streaming
- **`any`** for dynamic values (Go 1.18+ alias for `interface{}`)
- **`encoding/json`** for serialization (stdlib)
- **Zero external modules** — stdlib only

## Tests

```bash
cd runtimes/go && go test -v ./...
```

68 tests covering Payload, MutablePayload, State, Valve, Pipeline (batch + streaming).

## Constraints

- **Go 1.21+** minimum (uses `maps`, `slices` stdlib packages)
- **Zero external dependencies** — stdlib only
- **Value semantics** — Payload is a value type (struct), not a pointer
