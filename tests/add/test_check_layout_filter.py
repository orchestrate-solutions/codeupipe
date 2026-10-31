import pytest

from codeupipe import Payload
from codeupipe_add.check_layout_filter import CheckLayoutFilter
from codeupipe_add.refusal import Refusal


def check(layout):
    return CheckLayoutFilter().call(Payload({"layout": layout}))


def refused_with(layout):
    with pytest.raises(Refusal) as refused:
        check(layout)
    assert refused.value.exit_code == 2
    return str(refused.value)


def test_each_component_gets_every_key_and_root_becomes_the_directory():
    out = check({"lang": "python", "root": "src/pricing", "components": [
        {"kind": "filter", "name": "Discount", "description": "Takes a rate off the price."},
        {"kind": "pipeline", "name": "Pricing", "steps": ["Discount"], "hooks": []},
    ]})
    assert out.get("directory") == "src/pricing"
    assert out.get("components") == [
        {"kind": "filter", "name": "Discount", "description": "Takes a rate off the price.", "steps": [], "hooks": []},
        {"kind": "pipeline", "name": "Pricing", "description": "", "steps": ["Discount"], "hooks": []},
    ]


def test_with_no_root_the_directory_is_that_of_phase_1():
    assert check({"lang": "python", "components": [{"kind": "tap", "name": "Audit"}]}).get("directory") == "."


@pytest.mark.parametrize("layout, wanted", [
    ({"components": [{"kind": "tap", "name": "Audit"}]}, "lang"),
    ({"lang": "go", "components": [{"kind": "tap", "name": "Audit"}]}, "go"),
    ({"lang": "python"}, "components"),
    ({"lang": "python", "components": []}, "components"),
    ({"lang": "python", "components": "Audit"}, "components"),
    ({"lang": "python", "root": 3, "components": [{"kind": "tap", "name": "Audit"}]}, "root"),
    ({"lang": "python", "lanes": 2, "components": [{"kind": "tap", "name": "Audit"}]}, "lanes"),
    ({"lang": "python", "components": ["Audit"]}, "Audit"),
    ({"lang": "python", "components": [{"name": "Audit"}]}, "kind"),
    ({"lang": "python", "components": [{"kind": "tap"}]}, "name"),
    ({"lang": "python", "components": [{"kind": "pipeline", "name": "P", "step": ["A"]}]}, "step"),
    ({"lang": "python", "components": [{"kind": "tap", "name": "A", "description": 3}]}, "description"),
    ({"lang": "python", "components": [{"kind": "filter", "name": "A", "steps": ["B"]}]}, "only for a pipeline"),
    ({"lang": "python", "components": [{"kind": "tap", "name": "A", "hooks": ["B"]}]}, "only for a pipeline"),
    ({"lang": "python", "components": [{"kind": "pipeline", "name": "P", "steps": "A"}]}, "steps"),
    ({"lang": "python", "components": [{"kind": "pipeline", "name": "P", "steps": [{"valve": ["A"]}]}]}, "valve"),
    ({"lang": "python", "components": [{"kind": "pipeline", "name": "P", "steps": [{"tap": "A"}]}]}, "tap"),
    ({"lang": "python", "components": [{"kind": "pipeline", "name": "P", "hooks": [{"h": 1}]}]}, "hooks"),
])
def test_a_layout_that_breaks_a_rule_is_refused_and_the_message_names_what_is_wrong(layout, wanted):
    assert wanted in refused_with(layout)
