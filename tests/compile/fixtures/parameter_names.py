"""Fixture: steps whose Payload parameter is not called ``payload``. The
export must follow the name the author chose."""

from codeupipe.core import Pipeline


class DiscountFilter:
    def call(self, order):
        return order.insert("price", round(order.get("price", 0) * 0.9, 2))


class LabelFilter:
    def call(self, p):
        payload = "kept"  # a local that happens to be called payload
        same = p
        same.insert("label", payload)
        return same


class TotalFilter:
    def call(self, data):
        return data.insert("total", data.get("price", 0) * data.get("qty", 0))


class MarkBulkFilter:
    def call(self, order):
        return order.insert("bulk", True)


class AtLeastPredicate:
    def __init__(self, minimum):
        self.minimum = minimum

    def test(self, order):
        payload = self.minimum  # a local that happens to be called payload
        return order.get("qty", 0) >= payload


class AuditTap:
    def observe(self, seen):
        seen.get("price")


def build() -> Pipeline:
    pipeline = Pipeline()
    pipeline.add_filter(DiscountFilter())
    pipeline.add_filter(LabelFilter())
    pipeline.add_filter(TotalFilter())
    pipeline.add_valve(AtLeastPredicate(10), MarkBulkFilter())
    pipeline.add_tap(AuditTap())
    return pipeline
