"""The pricing pipeline: where the parts come together."""

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
