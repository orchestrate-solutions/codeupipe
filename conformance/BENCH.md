# Benchmark

A snapshot of `python conformance/bench.py`. Scenarios:
[bench/scenarios.json](bench/scenarios.json), in the conformance vocabulary.
Every target's output is checked against the others before its time counts.
Apple Silicon, one run.

These numbers are a snapshot for reading. The numbers that the speed check
compares are in `bench/baseline.json` (`python conformance/bench.py --check`,
[README.md](README.md)).

`python:run` is the dynamic run. The three `static-*` targets are the
compiles: `static-observe` records State and calls Hooks as `run` does; the
two fast modes do neither, and refuse the `hook` scenario rather than
silently dropping the Hook.

µs per run (best of 5 × 20,000, after 20,000 warmup runs); lower is better.

| scenario | steps | python:run | python:static-steps | python:static-inline | python:static-observe |
|---|---|---|---|---|---|
| `micro-pass` | 10 | 4.92 | 0.838 | 0.580 | 1.95 |
| `valve-gated` | 10 | 5.61 | 1.15 | 0.900 | 2.30 |
| `taps` | 13 | 5.21 | 0.887 | 0.629 | 2.07 |
| `hook` | 10 | 5.96 | — | — | 3.03 |
| `heavy-allocation` | 50 | 17.14 | 2.80 | 1.49 | 7.22 |

Not measured (the target refuses the scenario):
- python:static-steps hook: UnsupportedFilterShape: <pipeline>.call at line 0:0 — cannot lower Hook. Hint: Hooks do not run in the fast mode. Compile with observe=True (top-level Hooks only), or remove them.
- python:static-inline hook: UnsupportedFilterShape: <pipeline>.call at line 0:0 — cannot lower Hook. Hint: Hooks do not run in the fast mode. Compile with observe=True (top-level Hooks only), or remove them.
