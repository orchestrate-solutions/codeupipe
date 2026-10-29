from codeupipe import Payload
from codeupipe_add.render_layout_filter import RenderLayoutFilter


def rendered(*components):
    return RenderLayoutFilter().call(Payload({"components": list(components)})).get("components")


def test_a_component_with_no_steps_gets_the_text_of_phase_1():
    [discount] = rendered({"kind": "filter", "type_name": "DiscountFilter", "snake": "discount_filter",
                           "module": "app.discount_filter", "description": "Takes a rate off.",
                           "calls": [], "imports": []})
    assert '"""DiscountFilter: Takes a rate off."""' in discount["component_text"]
    assert "def call(self, payload):" in discount["component_text"]
    assert "Write the acceptance case for DiscountFilter." in discount["test_text"]


def test_a_pipeline_with_steps_imports_them_and_adds_them_in_order():
    [pricing] = rendered({"kind": "pipeline", "type_name": "PricingPipeline", "snake": "pricing_pipeline",
                          "module": "app.pricing_pipeline", "description": "",
                          "calls": [("add_filter", ["DiscountFilter"]),
                                    ("add_valve", ["AtLeastPredicate", "MarkBulkFilter"]),
                                    ("use_hook", ["PrintStepsHook"])],
                          "imports": [("app.at_least_predicate", "AtLeastPredicate"),
                                      ("app.discount_filter", "DiscountFilter"),
                                      ("app.mark_bulk_filter", "MarkBulkFilter"),
                                      ("app.print_steps_hook", "PrintStepsHook")]})
    assert pricing["component_text"] == '''"""PricingPipeline: TODO: say what PricingPipeline does."""

from codeupipe import Pipeline

from app.at_least_predicate import AtLeastPredicate
from app.discount_filter import DiscountFilter
from app.mark_bulk_filter import MarkBulkFilter
from app.print_steps_hook import PrintStepsHook


class PricingPipeline(Pipeline):
    """A Pipeline: its steps come from the layout."""

    def __init__(self):
        super().__init__()
        self.add_filter(DiscountFilter())
        self.add_valve(AtLeastPredicate(), MarkBulkFilter())
        self.use_hook(PrintStepsHook())
'''
    assert "Write the acceptance case for PricingPipeline." in pricing["test_text"]
