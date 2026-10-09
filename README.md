# codeupipe

> Write the pipeline once. Run it fully observable while you build it. Ship it
> with the framework compiled away. Prove the two runs never disagree.

CUP is four pieces, in Python, in two packages.

| Piece | What it does | Package | Reference |
|---|---|---|---|
| **Core** | The seven primitives: Payload, Filter, Pipeline, Valve, Tap, Hook, State. Stdlib only. A Tap that fails is recorded and never halts the run | `codeupipe` | [conformance/API.md](conformance/API.md) |
| **Compile** | Exports a pipeline as plain Python with no framework import. What cannot behave the same is refused, with the step named | `codeupipe` (`codeupipe.lower`) | [docs/static-export.md](docs/static-export.md) |
| **Config** | One optional file, six keys, so Lint and Compile run with no arguments | `codeupipe` (`codeupipe.config`) | [docs/config.md](docs/config.md) |
| **Lint** | Finds broken invariants before the code runs: anonymous steps, changes to a Payload behind its API, a Filter that reads State | `codeupipe-lint` | [packages/codeupipe-lint/README.md](packages/codeupipe-lint/README.md) |

This repo is a monorepo. It holds the two Python packages, the other six
runtimes, and the conformance suite that judges all of them. `codeupipe` has
no dependencies. `codeupipe-lint` depends only on `codeupipe`.

## A first pipeline

[examples/pricing.py](examples/pricing.py), in short:

```python
from codeupipe import Payload, Pipeline, Valve

class Discount:                      # a Filter: Payload in, new Payload out
    def __init__(self, rate):
        self.rate = rate
    def call(self, payload):
        return payload.insert("price", round(payload.get("price", 0) * (1 - self.rate), 2))

class AtLeast:                       # a predicate: an object with test(payload)
    def __init__(self, key, minimum):
        self.key, self.minimum = key, minimum
    def test(self, payload):
        return payload.get(self.key, 0) >= self.minimum

def build_pricing():
    pipeline = Pipeline()
    pipeline.add_filter(Discount(0.1))
    pipeline.add_filter(Valve(MarkBulk(), AtLeast("qty", 10)))   # runs only when the predicate holds
    pipeline.add_tap(AuditTap())                                 # observes; its failure never halts the run
    return pipeline

build_pricing().run(Payload({"price": 100.0, "qty": 12})).to_dict()
# {'price': 90.0, 'qty': 12, 'bulk': True}
```

Steps are classes in a module, not lambdas or functions in a script: a step
is identified by its type (`examples.pricing.Discount`), and State, Hooks and
the export all use that name. The linter says so before the runtime does.

```bash
python -m examples                   # run it, and print its State
```

## Run it

From the repo root.

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e packages/codeupipe -e packages/codeupipe-lint -r requirements-dev.txt
python -m pytest tests -q                        # core, lowering, lint, config, Python conformance
python conformance/run.py                        # every runtime, one judge
```

```bash
python -m codeupipe_lint.invariants                        # paths come from cup.config.json
python -m codeupipe_lint.anonymous_steps                   # the same
python -m codeupipe.lower examples.pricing:build_pricing --out build/pricing
```

The last command writes `build/pricing/src/steps/`. Nothing in it imports
`codeupipe`.

## How it is checked

- **Conformance.** 27 shared JSON cases, a runner per runtime, one judge.
  Python's three export targets are judged by the same cases as the dynamic
  run. Current state: [conformance/MATRIX.md](conformance/MATRIX.md).
- **Tests.** `tests/` mirrors the source: `core`, `lower`, `lint`, `config`,
  `conformance`, `scorecard`, `examples`. Checked on Python 3.9, 3.10, 3.12 and 3.14.
- **Scorecard.** Random pipelines run in all four modes and compared
  ([scorecard/README.md](scorecard/README.md)).

## Layout

| Path | What |
|---|---|
| `packages/codeupipe/` | The `codeupipe` package: Core (`core/`), Compile (`lower/`), Config (`config.py`) |
| `packages/codeupipe-lint/` | The `codeupipe-lint` package: `anonymous_steps` and `invariants` |
| `runtimes/` | The other six runtimes |
| `conformance/` | Cases, runners, the judge, and the benchmark ([BENCH.md](conformance/BENCH.md)) |
| `tests/` | The tests for both packages |
| `examples/` | The pipeline above, with its test in `tests/examples/` |
| `scorecard/` | Differential testing of the export |
| `docs/` | Reference for Compile and Config |

The root `pyproject.toml` is not a package. It holds the test settings.

## Other runtimes

TypeScript, Rust, Go, Kotlin, C# and C++ pass all 27 conformance cases and
have the anonymous-step lint. They do not have Compile or the invariant lint
yet; Python is first.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
