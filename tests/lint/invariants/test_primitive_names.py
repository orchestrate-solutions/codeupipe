"""CUP-I006 and CUP-I007: the name of a primitive, and the name of its file.

CUP-I007: the class name ends with its role (Filter, Tap, Hook, Predicate,
Pipeline). CUP-I006: the file name is the class name in snake_case.
"""

import pytest

from codeupipe import Payload
from codeupipe_lint.invariants.analyze_primitive_names_filter import AnalyzePrimitiveNamesFilter, snake_case
from codeupipe_lint.invariants.lint_pipeline import lint_paths
from codeupipe_lint.invariants.parse_python_filter import ParsePythonFilter
from codeupipe_lint.invariants.__main__ import main

FILTER = "class {name}:\n    def call(self, payload):\n        return payload\n"
TAP = "class {name}:\n    def observe(self, payload):\n        pass\n"
PREDICATE = "class {name}:\n    def test(self, payload):\n        return True\n"
HOOK = ("class {name}:\n    def before(self, step, payload):\n        pass\n\n"
        "    def after(self, step, payload):\n        pass\n\n"
        "    def on_error(self, step, error, payload):\n        pass\n")
PIPELINE = "from codeupipe import Pipeline\n\n\nclass {name}(Pipeline):\n    pass\n"
PLAIN = "class {name}:\n    def run(self):\n        pass\n"


def _file(tmp_path, file_name, template, class_name):
    path = tmp_path / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template.format(name=class_name))
    return str(path)


def analyze(path):
    parsed = ParsePythonFilter().call(Payload({"files": {"python": [path]}, "findings": [], "errors": []}))
    return AnalyzePrimitiveNamesFilter().call(parsed).get("findings")


def rules(path):
    return sorted(f.rule for f in analyze(path))


@pytest.mark.parametrize("name, expected", [
    ("Total", "total"), ("TotalFilter", "total_filter"), ("AtMostPredicate", "at_most_predicate"),
    ("ParseHTMLFilter", "parse_html_filter"), ("HTTPTap", "http_tap"), ("Step2Filter", "step2_filter"),
])
def test_snake_case(name, expected):
    assert snake_case(name) == expected


@pytest.mark.parametrize("template, class_name, file_name", [
    (FILTER, "TotalFilter", "total_filter.py"),
    (TAP, "LedgerTap", "ledger_tap.py"),
    (PREDICATE, "AtMostPredicate", "at_most_predicate.py"),
    (HOOK, "TimingHook", "timing_hook.py"),
    (PIPELINE, "BillingPipeline", "billing_pipeline.py"),
    (PLAIN, "Anything", "whatever.py"),
])
def test_a_correct_name_is_clean(tmp_path, template, class_name, file_name):
    assert analyze(_file(tmp_path, file_name, template, class_name)) == []


@pytest.mark.parametrize("template, class_name, role", [
    (FILTER, "Total", "Filter"), (TAP, "Ledger", "Tap"), (PREDICATE, "AtMost", "Predicate"),
    (HOOK, "Timing", "Hook"), (PIPELINE, "Billing", "Pipeline"),
])
def test_a_class_name_with_no_role_is_reported(tmp_path, template, class_name, role):
    path = _file(tmp_path, snake_case(class_name + role) + ".py", template, class_name)
    [finding] = analyze(path)
    assert finding.rule == "CUP-I007"
    assert class_name + role in finding.message


def test_a_file_name_that_is_not_the_class_name_is_reported(tmp_path):
    [finding] = analyze(_file(tmp_path, "total.py", FILTER, "TotalFilter"))
    assert finding.rule == "CUP-I006"
    assert "total_filter.py" in finding.message


def test_the_file_name_rule_asks_for_the_name_with_the_role(tmp_path):
    findings = analyze(_file(tmp_path, "total.py", FILTER, "Total"))
    assert sorted(f.rule for f in findings) == ["CUP-I006", "CUP-I007"]
    assert "total_filter.py" in [f for f in findings if f.rule == "CUP-I006"][0].message


def test_a_primitive_in_an_init_file_is_reported(tmp_path):
    assert rules(_file(tmp_path, "pkg/__init__.py", FILTER, "TotalFilter")) == ["CUP-I006"]


def test_test_files_are_not_checked(tmp_path):
    assert analyze(_file(tmp_path, "test_steps.py", FILTER, "Total")) == []
    assert analyze(_file(tmp_path, "tests/steps.py", FILTER, "Total")) == []


def test_the_rules_run_in_the_pipeline_and_can_be_switched_off(tmp_path):
    path = _file(tmp_path, "total.py", FILTER, "Total")
    assert {f.rule for f in lint_paths([path]).get("findings")} == {"CUP-I006", "CUP-I007"}
    assert lint_paths([path], disable=["CUP-I006", "CUP-I007"]).get("findings") == []


def test_a_comment_suppresses_one_class(tmp_path):
    path = tmp_path / "total.py"
    path.write_text("class Total:  # cup: allow-name\n    def call(self, payload):\n        return payload\n")
    out = lint_paths([str(path)])
    assert out.get("findings") == [] and len(out.get("suppressed")) == 2


def test_main_lists_the_rules(capsys):
    assert main(["--rules"]) == 0
    out = capsys.readouterr().out
    assert "CUP-I006  primitive-file-name" in out and "CUP-I007  primitive-role-suffix" in out
