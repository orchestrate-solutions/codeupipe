# Cross-runtime benchmark

Regenerate: `python conformance/bench.py`. Scenarios: [bench/scenarios.json](bench/scenarios.json)
(in the conformance vocabulary). Every runtime's output is
checked against the others before its time counts. Apple Silicon, one run.

µs per run (best of 5 × 20,000, after 20,000 warmup runs); lower is better.

| scenario | steps | python:run | python:static-steps | python:static-inline | python:static-observe | go:run | ts:run | rs:run | kt:run | cs:run | cpp:run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `micro-pass` | 10 | 7.80 | 1.46 | 0.593 | 2.55 | 2.29 | 1.37 | 2.21 | 0.475 | 1.62 | 1.25 |
| `valve-gated` | 10 | 10.56 | 1.85 | 0.854 | 2.96 | 2.59 | 1.50 | 2.90 | 0.630 | 1.79 | 1.92 |
| `taps` | 13 | 8.34 | 1.52 | 0.604 | 2.65 | 2.89 | 1.45 | 3.72 | 0.502 | 1.60 | 1.22 |
| `hook` | 10 | 8.72 | — | — | 3.42 | 2.89 | 3.12 | 3.45 | 0.523 | 1.65 | 1.22 |
| `heavy-allocation` | 50 | 36.90 | 9.93 | 1.43 | 14.09 | 39.47 | 8.99 | 66.17 | 14.57 | 22.19 | 56.16 |

## Python's static exports

Same scenarios, same machine, µs per run. `static-observe` records State and
calls Hooks exactly as `run` does (27/27 conformance); the fast exports do
neither, and refuse the `hook` scenario rather than silently dropping the
Hook.

| scenario | python:run | static-observe | static-steps | static-inline |
|---|---|---|---|---|
| micro-pass | 7.67 | 2.59 | 1.50 | 0.606 |
| valve-gated | 11.06 | 3.00 | 1.87 | 0.880 |
| taps | 8.44 | 2.70 | 1.51 | 0.631 |
| hook | 8.84 | 3.37 | refused | refused |
| heavy-allocation | 37.86 | 14.72 | 10.17 | 1.43 |

Observability in static code costs about 1.1 µs per 10 steps over the fast
per-step layout, and still runs about 3× faster than the dynamic runtime
for identical State and Hooks.

## Python's Payload overlay

Python's `Payload` overlays each write on its parent instead of copying
the dict (chains flatten every 32 writes). Same machine, same scenarios, µs per run:

| scenario | before | after | speed-up |
|---|---|---|---|
| micro-pass | 14.51 | 7.66 | 1.9× |
| valve-gated | 15.64 | 10.90 | 1.4× |
| taps | 15.82 | 8.55 | 1.9× |
| hook | 15.15 | 8.40 | 1.8× |
| heavy-allocation (50 inserts) | 71.43 | 37.14 | 1.9× |

## Reading the numbers

- **Dynamic dispatch, 10 steps:** Kotlin/JVM 0.57 µs, C++ 1.2, TypeScript/Bun
  1.3, Go 2.3, Rust 2.7, C# 2.9, Python 7.7.
- **Python static (`lowering="inline"`) runs at 0.62 µs,** on par with the
  JVM, because it is plain Python with the framework compiled away.
- **Copy-on-write dominates `heavy-allocation`:** every runtime except
  Python copies the whole map on each insert, so 50 inserts cost O(n²).
  TypeScript (8.9 µs) and the JVM (15.7) do it fastest; Rust (68.7) and
  C++ (57.1) are slowest, because their maps hold heap-allocated `String`
  keys and `Value` variants. The overlay that fixed Python applies to them
  too.
