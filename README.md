# codeupipe

> Write the pipeline once. Run it fully observable while you build it. Ship it
> with the framework compiled away. Prove the two runs never disagree.

CUP is four pieces, in Python, in two packages.

| Piece | What it does | Package | Reference |
|---|---|---|---|
| **Core** | The seven primitives: Payload, Filter, Pipeline, Valve, Tap, Hook, State. Stdlib only. A Tap that fails is recorded and never halts the run | `codeupipe` | [conformance/API.md](conformance/API.md) |
| **Compile** | Exports a pipeline as plain Python with no framework import. What cannot behave the same is refused, with the step named | `codeupipe` (`codeupipe.lower`) | [docs/static-export.md](docs/static-export.md) |
| **Config** | One optional file, six keys, so Lint and Compile run with no arguments | `codeupipe` (`codeupipe.config`) | [docs/config.md](docs/config.md) |
| **Lint** | Finds broken invariants before the code runs: anonymous steps, changes to a Payload behind its API, a Filter that reads State, a Tap or a Hook that writes, two primitives in one file | `codeupipe-lint` | [packages/codeupipe-lint/README.md](packages/codeupipe-lint/README.md) |

This repo holds the two Python packages and the conformance suite that
judges the dynamic run and the exports by the same cases. `codeupipe` has no
dependencies. `codeupipe-lint` depends only on `codeupipe`.

## A first pipeline

[examples/pricing/](examples/pricing/) has one primitive in each file. The
pipeline file is where they come together.

```
examples/pricing/
  discount.py      Filter
  mark_bulk.py     Filter
  at_least.py      predicate, the question a Valve asks
  audit_tap.py     Tap
  print_steps.py   Hook
  pipeline.py      Pipeline
```

A part knows nothing about the other parts, so you can test it alone and use
it again in another pipeline. The linter holds you to this: one primitive in
each file (`CUP-I005`).

```python
# discount.py — a Filter: takes the Payload, writes to it, returns it
class Discount:
    def __init__(self, rate):
        self.rate = rate

    def call(self, payload):
        return payload.insert("price", round(payload.get("price", 0) * (1 - self.rate), 2))
```

```python
# at_least.py — a predicate: an object with test(payload)
class AtLeast:
    def __init__(self, key, minimum):
        self.key = key
        self.minimum = minimum

    def test(self, payload):
        return payload.get(self.key, 0) >= self.minimum
```

```python
# pipeline.py — where the parts come together
from codeupipe import Pipeline, Valve

from .at_least import AtLeast
from .audit_tap import AuditTap
from .discount import Discount
from .mark_bulk import MarkBulk


def build_pricing():
    pipeline = Pipeline()
    pipeline.add_filter(Discount(0.1))
    pipeline.add_filter(Valve(MarkBulk(), AtLeast("qty", 10)))  # runs only when the predicate holds
    pipeline.add_tap(AuditTap())                                # its failure never halts the run
    return pipeline
```

```python
from codeupipe import Payload

build_pricing().run(Payload({"price": 100.0, "qty": 12})).to_dict()
# {'price': 90.0, 'qty': 12, 'bulk': True}
```

A step is a class in a module, not a lambda or a function in a script: it is
identified by its type (`examples.pricing.discount.Discount`), and State,
Hooks and the export all use that identity. The linter says so before the
runtime does.

```bash
python -m examples.pricing           # run it with a Hook, and print its State
```

## Run it

From the repo root.

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install --upgrade pip           # an editable install needs pip 21.3 or later
python -m pip install -e packages/codeupipe -e packages/codeupipe-lint -r requirements-dev.txt
python -m pytest tests -q                        # core, lowering, lint, config, Python conformance
python conformance/run.py                        # the dynamic run and the exports, one judge
```

```bash
python -m codeupipe_lint.invariants                        # paths come from cup.config.json
python -m codeupipe_lint.anonymous_steps                   # the same
python -m codeupipe.lower examples.pricing.pipeline:build_pricing --out build/pricing
```

The last command writes `build/pricing/src/steps/`. Nothing in it imports
`codeupipe`.

## How it is checked

- **Conformance.** 27 JSON cases, one judge. The three export targets are
  judged by the same cases as the dynamic run. Current state: [conformance/MATRIX.md](conformance/MATRIX.md).
- **Tests.** `tests/` mirrors the source: `core`, `lower`, `lint`, `config`,
  `conformance`, `scorecard`, `examples`. Checked on Python 3.9, 3.10, 3.12 and 3.14.
- **Scorecard.** Random pipelines run in all four modes and compared
  ([scorecard/README.md](scorecard/README.md)).

## Layout

| Path | What |
|---|---|
| `packages/codeupipe/` | The `codeupipe` package: Core (`core/`), Compile (`lower/`), Config (`config.py`) |
| `packages/codeupipe-lint/` | The `codeupipe-lint` package: `anonymous_steps` and `invariants` |
| `conformance/` | Cases, runners, the judge, and the benchmark ([BENCH.md](conformance/BENCH.md)) |
| `tests/` | The tests for both packages |
| `examples/pricing/` | The pipeline above, one primitive in each file, with its test in `tests/examples/` |
| `scorecard/` | Differential testing of the export |
| `docs/` | Reference for Compile and Config |

The root `pyproject.toml` is not a package. It holds the test settings.

## Other languages

This release is Python. The contract ([conformance/API.md](conformance/API.md))
and the conformance cases are language-neutral: a runtime in another
language is written to the contract and added with its conformance runner.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
