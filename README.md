# codeupipe

codeupipe is a Python library for writing a program as a pipeline of small
steps.

- A **Payload** holds the data.
- A **Filter** changes the Payload.
- A **Valve** runs a Filter only when a condition is true.
- A **Tap** reads the Payload.
- A **Hook** is called before and after each step.
- **State** records which steps ran.
- A **Pipeline** runs the steps in order.

If you know Unix, these are close to things you know.

| codeupipe | Unix |
|---|---|
| Pipeline | A pipeline. A codeupipe pipeline sends one Payload through its steps, one step after another |
| Filter | A filter, such as `sort` or `tr` |
| Valve and predicate | `test condition && command`, or the address of a `sed` command |
| Tap | `tee` |
| Hook | A git hook: code that runs before and after a step |
| State | `$?` and `PIPESTATUS` |

This repository has two packages.

| Package | Contents | Reference |
|---|---|---|
| `codeupipe` | The seven primitives. An export command that writes a pipeline as plain Python with no import of codeupipe. A config file reader. No dependencies | [conformance/API.md](conformance/API.md), [docs/static-export.md](docs/static-export.md), [docs/config.md](docs/config.md) |
| `codeupipe-lint` | Two linters for pipeline code. Depends on `codeupipe` only | [packages/codeupipe-lint/README.md](packages/codeupipe-lint/README.md) |

## Status

Not released. The repository is in review. Python 3.9 or later.

## Example

[examples/pricing/](examples/pricing/) has one class in each file. The
pipeline file imports them and adds them.

```
examples/pricing/
  discount_filter.py      Filter
  mark_bulk_filter.py     Filter
  at_least_predicate.py   predicate (the condition of a Valve)
  audit_tap.py            Tap
  print_steps_hook.py     Hook
  pricing_pipeline.py     Pipeline
```

A class name ends with its role. The file name is the class name in
snake_case.

```python
# discount_filter.py
class DiscountFilter:
    def __init__(self, rate):
        self.rate = rate

    def call(self, payload):
        return payload.insert("price", round(payload.get("price", 0) * (1 - self.rate), 2))
```

```python
# at_least_predicate.py
class AtLeastPredicate:
    def __init__(self, key, minimum):
        self.key = key
        self.minimum = minimum

    def test(self, payload):
        return payload.get(self.key, 0) >= self.minimum
```

```python
# pricing_pipeline.py
from codeupipe import Pipeline

from .at_least_predicate import AtLeastPredicate
from .audit_tap import AuditTap
from .discount_filter import DiscountFilter
from .mark_bulk_filter import MarkBulkFilter


class PricingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.add_filter(DiscountFilter(0.1))
        # MarkBulkFilter runs only when the predicate is true.
        self.add_valve(AtLeastPredicate("qty", 10), MarkBulkFilter())
        # A Tap failure is recorded and does not stop the run.
        self.add_tap(AuditTap())
```

```python
from codeupipe import Payload

PricingPipeline().run(Payload({"price": 100.0, "qty": 12})).to_dict()
# {'price': 90.0, 'qty': 12, 'bulk': True}
```

A Valve is made in the pipeline file, from two parts: `add_valve(predicate,
filter)`. The predicate is the condition. The Filter runs only when
`predicate.test(payload)` is true. There is no Valve file.

A step must be a class in a module. A lambda, or a class in the script that
you run, is refused. The reason is step identity: a step is identified by its
type, for example `examples.pricing.discount_filter.DiscountFilter`. State,
Hooks and the export use that identity.

```bash
python -m examples.pricing
```

This command runs the pipeline with a Hook and prints its State.

## Install for development

Run these commands from the repository root.

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e packages/codeupipe -e packages/codeupipe-lint -r requirements-dev.txt
```

An editable install needs pip 21.3 or later.

## Commands

| Command | What it does |
|---|---|
| `python -m pytest tests -q` | Runs the tests |
| `python conformance/run.py` | Runs the 27 conformance cases against the dynamic run and the three exports |
| `python -m codeupipe_lint.anonymous_steps` | Runs the anonymous-step linter. Paths come from `cup.config.json` |
| `python -m codeupipe_lint.invariants` | Runs the invariant linter. Paths come from `cup.config.json` |
| `python -m codeupipe.lower examples.pricing.pricing_pipeline:PricingPipeline --out build/pricing` | Exports the example to `build/pricing/src/steps/` |
| `python conformance/bench.py --check` | Compares benchmark numbers with the recorded baseline. Fails outside 25% |
| `python -m scorecard.differential` | Compares the export with the dynamic run on random pipelines |

## Layout

| Path | Contents |
|---|---|
| `packages/codeupipe/` | The `codeupipe` package: `core/`, `lower/` (the export), `config.py` |
| `packages/codeupipe-lint/` | The `codeupipe-lint` package: `anonymous_steps/`, `invariants/` |
| `conformance/` | The contract ([API.md](conformance/API.md)), the cases, the runner, the benchmark |
| `tests/` | The tests for the two packages |
| `examples/pricing/` | The example, with its test in `tests/examples/` |
| `scorecard/` | The comparison of the export with the dynamic run on random pipelines |
| `docs/` | Reference for the export and the config file |

The root `pyproject.toml` is not a package. It holds the test settings.

## Other languages

This repository is Python only. The contract and the conformance cases do
not depend on Python. A runtime in another language must implement the
contract and add a conformance runner.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
