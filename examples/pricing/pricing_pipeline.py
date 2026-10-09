"""PricingPipeline: the place where the parts come together."""

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
