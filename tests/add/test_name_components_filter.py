import pytest

from codeupipe import Payload
from codeupipe_add.name_components_filter import NameComponentsFilter
from codeupipe_add.refusal import Refusal


def component(kind, name):
    return {"kind": kind, "name": name, "description": "", "steps": [], "hooks": []}


def named(components, directory="src/pricing"):
    return NameComponentsFilter().call(Payload({"components": components, "directory": directory})).get("components")


def test_each_component_gets_the_names_and_paths_of_phase_1():
    [discount] = named([component("filter", "Discount")])
    assert discount["type_name"] == "DiscountFilter"
    assert discount["component_path"] == "src/pricing/discount_filter.py"
    assert discount["test_path"] == "tests/test_discount_filter.py"
    assert discount["module"] == "src.pricing.discount_filter"


def test_a_name_that_phase_1_refuses_is_refused():
    with pytest.raises(Refusal) as refused:
        named([component("filter", "Take Rate")])
    assert refused.value.exit_code == 2 and "Take Rate" in str(refused.value)


def test_two_components_with_the_same_type_name_are_refused():
    with pytest.raises(Refusal) as refused:
        named([component("filter", "Discount"), component("filter", "DiscountFilter")])
    assert refused.value.exit_code == 2 and "DiscountFilter" in str(refused.value)
