"""Fixture: steps whose methods carry type hints. The export must erase
them, as a compiler erases types."""

from typing import List, Optional, TypedDict

from codeupipe.core import Payload, Pipeline


class Order(TypedDict):
    price: float
    qty: int


class Totalled(TypedDict):
    total: float


class Flagged(TypedDict, total=False):
    bulk: bool


class AddTotal:
    def call(self, payload: Payload[Order]) -> Payload[Totalled]:
        lines: List[float] = [payload.get("price")] * payload.get("qty")
        note: Optional[str]
        return payload.insert("total", sum(lines))


class FlagBulk:
    def call(self, payload: Payload[Order]) -> Payload[Flagged]:
        return payload.insert("bulk", True)


class IsBulk:
    def __init__(self, at_least: int):
        self.at_least = at_least

    def test(self, payload: Payload[Order]) -> bool:
        return payload.get("qty") >= self.at_least


class Audit:
    def observe(self, payload: Payload[Order]) -> None:
        payload.get("price")


def build() -> Pipeline:
    pipeline = Pipeline()
    pipeline.add_filter(AddTotal())
    pipeline.add_valve(IsBulk(10), FlagBulk())
    pipeline.add_tap(Audit())
    return pipeline
