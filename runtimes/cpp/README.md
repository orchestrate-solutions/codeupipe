# codeupipe — C++ runtime

Header-only **C++20** port of codeupipe. Zero external runtime dependencies.
The seven CUP primitives — **Payload · Filter · Pipeline · Valve · Tap · Hook ·
State** — with identical semantics to the Python, TypeScript, Rust, Go, C#,
and Kotlin runtimes.

## Design

- **Header-only core** under [`include/codeupipe/`](./include/codeupipe/).
- **C++20** baseline: concepts, `std::variant`, `std::span` where useful.
- **Payload** = `shared_ptr<const map>` copy-on-write. Immutable at the API.
- **Filter** = concept + type-erased `IFilter` for heterogeneous Pipelines;
  `add_*` are templates, so the concrete type (the step's identity) is known.
- **Pipeline** = ordered `std::variant<FilterStep, TapStep>`. Blueprint
  inspectable via `pipeline.steps()`.
- **State** kept OUT of Payload. Filters are blind to State by contract.
- **Tap** errors are swallowed. Removing all Taps yields identical output.

## Step identity

Steps have no names. Each is identified by its type's qualified name, taken
at compile time from the compiler's function signature (no RTTI), `#2` from
the second use; State and Hooks report it (conformance/API.md, "Step
identity"; `include/codeupipe/step_identity.hpp`).

```cpp
namespace app {
struct Clean final : cup::IFilter { cup::Payload call(const cup::Payload& p) override; };
struct Positive { bool test(const cup::Payload& p) const; };        // a predicate object
struct Onboarding : cup::Pipeline { Onboarding(); };               // nested: a named subclass
}
pipe.add_filter(app::Clean{})                                       // "app::Clean"
    .add_filter(cup::Valve(app::Clean{}, app::Positive{}))          // "app::Clean#2"
    .add_pipeline(app::Onboarding{});                               // "app::Onboarding"
```

Refused at **compile time** (`static_assert`): lambdas (and the removed
`make_filter`/`make_tap` lambda adapters), function-pointer predicates (a
function pointer carries only its signature, so predicates are objects
with `test()`, configuration in members), types in an anonymous namespace (not
unique across translation units, not testable from another file), a
`unique_ptr` instead of the step itself, and a plain `Pipeline` nested as a
step. A struct declared inside a function looks like a global type to
Clang; the linter catches it.

## Build

```bash
cd runtimes/cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
./build/cup_bench            # micro-bench, emits JSON
./build/clean_validate_save  # canonical example
```

Catch2 is fetched at configure time as a test-only dependency.

## Benchmark

`bench/bench_hop.cpp` runs N filters × M iterations and prints one JSON line
that the polyglot matrix ([`bench/bench_polyglot_hop.py`](../../bench/bench_polyglot_hop.py))
can consume alongside the other runtimes:

```json
{"runtime":"cpp","filters":8,"iterations":100000,"ns_per_iter":...,"ns_per_hop":...,"ops_per_sec":...}
```

## Invariants (enforced by test)

1. Removing all Taps and Hooks yields the identical Pipeline output.
2. Same Payload in, same Payload out — deterministic.

See [`tests/test_invariants.cpp`](./tests/test_invariants.cpp).
