import pytest

from codeupipe import Payload
from codeupipe_add.refusal import Refusal
from codeupipe_add.type_name_filter import TypeNameFilter


def named(kind, name):
    out = TypeNameFilter().call(Payload({"kind": kind, "name": name}))
    return out.get("type_name"), out.get("snake")


@pytest.mark.parametrize("kind, name, type_name, snake", [
    ("filter", "Discount", "DiscountFilter", "discount_filter"),
    ("filter", "DiscountFilter", "DiscountFilter", "discount_filter"),
    ("predicate", "at_least", "AtLeastPredicate", "at_least_predicate"),
    ("tap", "audit-log", "AuditLogTap", "audit_log_tap"),
    ("filter", "HTTPGet", "HTTPGetFilter", "http_get_filter"),
    ("hook", "printSteps", "PrintStepsHook", "print_steps_hook"),
    ("pipeline", "Pricing", "PricingPipeline", "pricing_pipeline"),
])
def test_the_type_name_has_its_role_and_the_file_name_the_rule_of_the_linters(kind, name, type_name, snake):
    assert named(kind, name) == (type_name, snake)


@pytest.mark.parametrize("kind, name, wanted", [
    ("valve", "AtLeast", "add_valve(predicate, filter)"),
    ("payload", "Order", "runtime"),
    ("widget", "Thing", "filter, predicate, tap, hook, pipeline"),
    ("filter", "2Fast", "2Fast"),
    ("filter", "Take Rate", "Take Rate"),
    ("filter", "", "name"),
])
def test_a_kind_or_a_name_that_cannot_be_used_is_refused_with_exit_2(kind, name, wanted):
    with pytest.raises(Refusal) as refused:
        named(kind, name)
    assert refused.value.exit_code == 2 and wanted in str(refused.value)
