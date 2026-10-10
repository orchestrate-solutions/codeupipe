# codeupipe

codeupipe is a Python library for writing a program as a pipeline of small
steps. It has no dependencies. Python 3.9 or later.

```bash
pip install codeupipe
```

## The eight primitives

| Primitive | What it does | Who writes it |
|---|---|---|
| **Payload** | Carries the data | The library |
| **Filter** | Changes the data | You |
| **Predicate** | Asks a yes-or-no question about the data | You |
| **Valve** | Joins a Predicate to a Filter: the Filter runs when the answer is yes | The library. You add one with `add_valve(predicate, filter)` |
| **Tap** | Reads the data as it goes by | You |
| **Hook** | Is called before and after each step | You |
| **State** | Records which steps ran | The library |
| **Pipeline** | Runs the steps in order | You |

## Example

Each class is in its own file. The pipeline file imports them and adds them.

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

A step is a class. State and Hooks report each step by the name of its
class, for example `DiscountFilter`. A lambda is refused, because it does not
have the method of a step.

## What is in the package

- `codeupipe`: the eight primitives.
- `python -m codeupipe.lower`: writes a pipeline as plain Python with no
  import of codeupipe.
- `codeupipe.config`: reads `cup.config.json`.

The linter is a separate package, `codeupipe-lint`. Its install command is
in the repository README.

## Documentation

- The contract: https://github.com/orchestrate-solutions/codeupipe/blob/main/conformance/API.md
- The export: https://github.com/orchestrate-solutions/codeupipe/blob/main/docs/static-export.md
- The config file: https://github.com/orchestrate-solutions/codeupipe/blob/main/docs/config.md
- The repository: https://github.com/orchestrate-solutions/codeupipe

## License

Apache License 2.0.
