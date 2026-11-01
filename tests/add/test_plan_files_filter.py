from codeupipe import Payload
from codeupipe_add.plan_files_filter import PlanFilesFilter


def plan(directory):
    out = PlanFilesFilter().call(Payload({"directory": directory, "snake": "discount_filter"}))
    return out.get("component_path"), out.get("test_path"), out.get("module")


def test_the_component_goes_in_the_directory_and_the_test_in_tests():
    assert plan(".") == ("discount_filter.py", "tests/test_discount_filter.py", "discount_filter")
    assert plan("src/pricing") == ("src/pricing/discount_filter.py", "tests/test_discount_filter.py",
                                   "src.pricing.discount_filter")
    assert plan("./src/") == ("src/discount_filter.py", "tests/test_discount_filter.py", "src.discount_filter")
