"""The pricing pipeline: where the parts come together."""

from codeupipe import Pipeline, Valve

from .at_least_predicate import AtLeastPredicate
from .audit_tap import AuditTap
from .discount_filter import DiscountFilter
from .mark_bulk_filter import MarkBulkFilter


def build_pricing():
    pipeline = Pipeline()
    pipeline.add_filter(DiscountFilter(0.1))
    # MarkBulkFilter runs only when the predicate is true.
    pipeline.add_filter(Valve(MarkBulkFilter(), AtLeastPredicate("qty", 10)))
    # A Tap failure is recorded and does not stop the run.
    pipeline.add_tap(AuditTap())
    return pipeline
