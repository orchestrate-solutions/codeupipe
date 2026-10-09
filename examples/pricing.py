"""A small pipeline that uses a Filter, a Valve and a Tap.

Run it:      python -m examples
Export it:   python -m codeupipe.lower examples.pricing:build_pricing --out build/pricing

The steps are in this module and the run is in ``__main__.py``: a step defined
in the entry script is refused, because its identity would change with how the
program is started.
"""

from codeupipe import Payload, Pipeline, Valve


class Discount:
    """Filter: takes a Payload, returns a new one."""

    def __init__(self, rate):
        self.rate = rate

    def call(self, payload):
        return payload.insert("price", round(payload.get("price", 0) * (1 - self.rate), 2))


class MarkBulk:
    def call(self, payload):
        return payload.insert("bulk", True)


class AtLeast:
    """Predicate: an object with test(payload), so it has a name and can be tested alone."""

    def __init__(self, key, minimum):
        self.key = key
        self.minimum = minimum

    def test(self, payload):
        return payload.get(self.key, 0) >= self.minimum


class AuditTap:
    """Tap: observes and returns nothing. Its failure is recorded and never halts the run."""

    def observe(self, payload):
        raise ConnectionError("audit sink is down")


def build_pricing():
    pipeline = Pipeline()
    pipeline.add_filter(Discount(0.1))
    pipeline.add_filter(Valve(MarkBulk(), AtLeast("qty", 10)))
    pipeline.add_tap(AuditTap())
    return pipeline

