import pytest

from codeupipe import Payload
from codeupipe_add.refusal import Refusal
from codeupipe_add.resolve_steps_filter import ResolveStepsFilter

ROLES = {"filter": "Filter", "predicate": "Predicate", "tap": "Tap", "hook": "Hook", "pipeline": "Pipeline"}


def component(kind, name, steps=(), hooks=()):
    type_name = name + ROLES[kind]
    return {"kind": kind, "name": name, "type_name": type_name, "module": "app." + type_name.lower(),
            "steps": list(steps), "hooks": list(hooks)}


def resolve(*components):
    return ResolveStepsFilter().call(Payload({"components": list(components)})).get("components")


def refused_with(*components):
    with pytest.raises(Refusal) as refused:
        resolve(*components)
    assert refused.value.exit_code == 2
    return str(refused.value)


def test_each_step_becomes_the_call_of_its_kind_in_order():
    *_, pricing = resolve(
        component("filter", "Discount"), component("predicate", "AtLeast"), component("filter", "MarkBulk"),
        component("tap", "Audit"), component("hook", "PrintSteps"), component("pipeline", "Tax"),
        component("pipeline", "Pricing", steps=["Discount", {"valve": ["AtLeast", "MarkBulkFilter"]}, "Audit", "Tax"],
                  hooks=["PrintSteps"]))
    assert pricing["calls"] == [("add_filter", ["DiscountFilter"]),
                                ("add_valve", ["AtLeastPredicate", "MarkBulkFilter"]),
                                ("add_tap", ["AuditTap"]),
                                ("add_pipeline", ["TaxPipeline"]),
                                ("use_hook", ["PrintStepsHook"])]
    assert pricing["imports"] == [("app.atleastpredicate", "AtLeastPredicate"), ("app.audittap", "AuditTap"),
                                  ("app.discountfilter", "DiscountFilter"), ("app.markbulkfilter", "MarkBulkFilter"),
                                  ("app.printstepshook", "PrintStepsHook"), ("app.taxpipeline", "TaxPipeline")]


def test_a_step_used_twice_is_imported_once_and_a_component_with_no_steps_has_no_calls():
    discount, pricing = resolve(component("filter", "Discount"),
                                component("pipeline", "Pricing", steps=["Discount", "Discount"]))
    assert discount["calls"] == [] and discount["imports"] == []
    assert pricing["imports"] == [("app.discountfilter", "DiscountFilter")]


def test_a_name_that_is_not_a_component_of_the_file_is_refused():
    assert "Rebate" in refused_with(component("pipeline", "Pricing", steps=["Rebate"]))


@pytest.mark.parametrize("steps, hooks, wanted", [
    (["AtLeast"], [], "valve"),
    (["PrintSteps"], [], "hooks"),
    ([{"valve": ["Discount", "Discount"]}], [], "Discount is a filter, not a predicate"),
    ([{"valve": ["AtLeast", "Audit"]}], [], "Audit is a tap, not a filter"),
    ([], ["Discount"], "hook"),
])
def test_a_step_of_the_wrong_kind_is_refused(steps, hooks, wanted):
    assert wanted in refused_with(component("filter", "Discount"), component("predicate", "AtLeast"),
                                  component("tap", "Audit"), component("hook", "PrintSteps"),
                                  component("pipeline", "Pricing", steps=steps, hooks=hooks))


def test_a_pipeline_that_has_itself_as_a_step_is_refused_directly_or_through_another():
    assert "Pricing" in refused_with(component("pipeline", "Pricing", steps=["Pricing"]))
    message = refused_with(component("pipeline", "Pricing", steps=["Tax"]),
                           component("pipeline", "Tax", steps=["Pricing"]))
    assert "PricingPipeline" in message and "TaxPipeline" in message
