"""A pipeline over a type of your own.

Payload is the default: a map that any developer can read. A type of your
own can take its place. The Pipeline asks one thing of it, ``copy()``, for
the copy that a run works on. Lineage is kept only by a type that has
``_stamp(label)``; for any other type, turning lineage on does nothing.
"""

import asyncio
import dataclasses
from typing import Optional

import pytest

from codeupipe import Hook, Pipeline


@dataclasses.dataclass
class Order:
    price: float
    qty: int
    bulk: bool = False

    def copy(self):
        return dataclasses.replace(self)


@dataclasses.dataclass
class TracedOrder(Order):
    steps: list = dataclasses.field(default_factory=list)

    def copy(self):
        return dataclasses.replace(self, steps=list(self.steps))

    def _stamp(self, label):
        self.steps.append(label)


class DiscountFilter:
    def call(self, order):
        order.price = round(order.price * 0.9, 2)
        return order


class MarkBulkFilter:
    def call(self, order):
        order.bulk = True
        return order


class RefuseFreeFilter:
    def call(self, order):
        if order.price <= 0:
            raise ValueError("an order must cost something")
        return order


class AtLeastPredicate:
    def test(self, order):
        return order.qty >= 10


class SeeTap:
    def __init__(self):
        self.seen = []

    def observe(self, order):
        self.seen.append(order.price)


class RecordHook(Hook):
    def __init__(self):
        super().__init__()
        self.events = []

    def before(self, step: Optional[str], payload) -> None:
        self.events.append(f"before:{step or ''}")

    def on_error(self, step: Optional[str], error: Exception, payload) -> None:
        self.events.append(f"error:{step or ''}:{payload.price}")


class PricingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.add_filter(DiscountFilter())
        self.add_valve(AtLeastPredicate(), MarkBulkFilter())


def _pricing():
    return PricingPipeline()


def test_every_primitive_takes_the_type():
    tap, hook = SeeTap(), RecordHook()
    pipeline = _pricing()
    pipeline.add_tap(tap)
    pipeline.use_hook(hook)
    given = Order(100.0, 12)
    out = pipeline.run(given)
    assert out == Order(90.0, 12, True)
    assert given == Order(100.0, 12)  # the caller's value is not changed
    assert tap.seen == [90.0]
    assert pipeline.state.executed == ["DiscountFilter", "MarkBulkFilter", "SeeTap"]
    assert hook.events == ["before:", "before:DiscountFilter", "before:MarkBulkFilter"]
    pipeline.run(Order(100.0, 2))
    assert pipeline.state.skipped == ["MarkBulkFilter"]


def test_the_fast_path_and_run_async_take_the_type():
    assert _pricing().run(Order(100.0, 12)) == Order(90.0, 12, True)
    assert asyncio.run(_pricing().run_async(Order(100.0, 12))) == Order(90.0, 12, True)


def test_a_nested_pipeline_takes_the_type():
    pipeline = Pipeline()
    pipeline.add_pipeline(PricingPipeline())
    pipeline.add_filter(RefuseFreeFilter())
    assert pipeline.run(Order(50.0, 10)) == Order(45.0, 10, True)


def test_a_failure_is_the_same_as_with_a_payload():
    hook = RecordHook()
    pipeline = Pipeline()
    pipeline.add_filter(DiscountFilter())
    pipeline.add_filter(RefuseFreeFilter())
    pipeline.use_hook(hook)
    with pytest.raises(ValueError, match="must cost something"):
        pipeline.run(Order(0.0, 1))
    assert pipeline.state.executed == ["DiscountFilter"]
    assert hook.events[-2:] == ["error:RefuseFreeFilter:0.0", "error::0.0"]


@pytest.mark.parametrize("run", ["sync", "async"])
def test_lineage_does_nothing_for_a_type_without_stamp(run):
    pipeline = _pricing()
    pipeline.observe(lineage=True)
    given = Order(100.0, 12)
    out = pipeline.run(given) if run == "sync" else asyncio.run(pipeline.run_async(given))
    assert out == Order(90.0, 12, True)
    assert pipeline.state.executed == ["DiscountFilter", "MarkBulkFilter"]


@pytest.mark.parametrize("run", ["sync", "async"])
def test_lineage_is_kept_by_a_type_with_stamp(run):
    pipeline = _pricing()
    pipeline.observe(lineage=True)
    given = TracedOrder(100.0, 12)
    out = pipeline.run(given) if run == "sync" else asyncio.run(pipeline.run_async(given))
    assert out.steps == ["DiscountFilter", "MarkBulkFilter"]
    assert given.steps == []
