# Benchmark

A snapshot of `python conformance/bench.py`. Scenarios:
[bench/scenarios.json](bench/scenarios.json), in the conformance vocabulary.
Every target's output is checked against the others before its time counts.
Apple Silicon, one run.

These numbers are a snapshot for reading. Nothing fails because of them: CI
measures again on every run and keeps the numbers, and does not compare them
([README.md](README.md)).

`python:run` is the dynamic run. The three `static-*` targets are the
compiles: `static-observe` records State and calls Hooks as `run` does; the
two fast modes do neither, and refuse the `hook` scenario rather than
silently dropping the Hook.

`rust:run` is the dynamic run of the Rust crate, built with `--release`. It
records State and calls Hooks as `python:run` does. `go:run` is the dynamic
run of the Go package, which does the same.

µs per run (best of 5 × 20,000, after 20,000 warmup runs); lower is better.

| scenario | steps | python:run | python:static-steps | python:static-inline | python:static-observe | rust:run | go:run |
|---|---|---|---|---|---|---|---|
| `micro-pass` | 10 | 4.79 | 0.824 | 0.627 | 1.93 | 0.276 | 0.546 |
| `valve-gated` | 10 | 5.14 | 1.11 | 0.860 | 2.26 | 0.326 | 0.612 |
| `taps` | 13 | 5.03 | 0.895 | 0.626 | 2.03 | 0.293 | 0.567 |
| `hook` | 10 | 5.41 | — | — | 2.98 | 0.286 | 0.626 |
| `heavy-allocation` | 50 | 15.03 | 2.87 | 1.51 | 7.21 | 2.31 | 2.15 |

`rust:run` on `heavy-allocation` was 4.40 µs before the change for
[#20](https://github.com/orchestrate-solutions/codeupipe/issues/20): a new
key no longer allocates when it is short, and the index no longer copies
the key. The other Rust numbers did not change.

Not measured (the target refuses the scenario):
- python:static-steps hook: UnsupportedFilterShape: <pipeline>.call at line 0:0 — cannot lower Hook. Hint: Hooks do not run in the fast static export. Export with observe=True (top-level Hooks only), or remove them.
- python:static-inline hook: UnsupportedFilterShape: <pipeline>.call at line 0:0 — cannot lower Hook. Hint: Hooks do not run in the fast static export. Export with observe=True (top-level Hooks only), or remove them.

