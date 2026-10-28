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
records State and calls Hooks as `python:run` does.

µs per run (best of 5 × 20,000, after 20,000 warmup runs); lower is better.

| scenario | steps | python:run | python:static-steps | python:static-inline | python:static-observe | rust:run |
|---|---|---|---|---|---|---|
| `micro-pass` | 10 | 4.94 | 0.824 | 0.606 | 1.92 | 0.246 |
| `valve-gated` | 10 | 5.81 | 1.11 | 0.801 | 2.25 | 0.301 |
| `taps` | 13 | 5.34 | 0.899 | 0.602 | 2.03 | 0.256 |
| `hook` | 10 | 5.88 | — | — | 2.97 | 0.247 |
| `heavy-allocation` | 50 | 16.05 | 2.84 | 1.49 | 7.01 | 4.24 |

Not measured (the target refuses the scenario):
- python:static-steps hook: UnsupportedFilterShape: <pipeline>.call at line 0:0 — cannot lower Hook. Hint: Hooks do not run in the fast static export. Export with observe=True (top-level Hooks only), or remove them.
- python:static-inline hook: UnsupportedFilterShape: <pipeline>.call at line 0:0 — cannot lower Hook. Hint: Hooks do not run in the fast static export. Export with observe=True (top-level Hooks only), or remove them.
