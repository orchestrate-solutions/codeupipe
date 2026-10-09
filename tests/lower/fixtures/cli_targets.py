"""Fixture: things `python -m codeupipe.lower module:name` can be pointed at."""

from codeupipe.core import Pipeline, Valve

from tests.lower.fixtures.instance_config import AtLeast, Discount, HoldsAnObject, SetFlag
from tests.lower.fixtures.plane_b import ExplodingTap

PRICING = Pipeline()
PRICING.add_filter(Discount(0.1))
PRICING.add_filter(Valve(SetFlag("bulk"), AtLeast("qty", 10)))
PRICING.add_tap(ExplodingTap())


def build_pricing():
    pipeline = Pipeline()
    pipeline.add_filter(Discount(0.5))
    return pipeline


class Checkout(Pipeline):
    def __init__(self):
        super().__init__()
        self.add_filter(Discount(0.25))


REFUSED = Pipeline()
REFUSED.add_filter(Discount(0.1))
REFUSED.add_filter(HoldsAnObject())

NOT_A_PIPELINE = 42


def needs_an_argument(rate):
    return Pipeline()


def returns_something_else():
    return {"not": "a pipeline"}
