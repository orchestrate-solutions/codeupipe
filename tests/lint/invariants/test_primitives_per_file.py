"""CUP-I005: one primitive in each file."""

import shutil

from codeupipe import Payload
from codeupipe_lint.invariants.analyze_primitives_per_file_filter import AnalyzePrimitivesPerFileFilter
from codeupipe_lint.invariants.lint_pipeline import lint_paths
from codeupipe_lint.invariants.parse_python_filter import ParsePythonFilter
from codeupipe_lint.invariants.__main__ import main

from ._support import by_line, expectations, fixture

POSITIVE = fixture("primitives_per_file_positive.py")
NEGATIVE = fixture("primitives_per_file_negative.py")
SUPPRESSED = fixture("primitives_per_file_suppressed.py")
NAME_RULES = ["CUP-I006", "CUP-I007"]  # the fixtures are about one rule; their names are not the subject


def _outside_tests(tmp_path, source, name="steps.py"):
    """Test files are not checked, and the fixtures live under tests/: check a copy."""
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, target)
    return str(target)


def analyze(path):
    parsed = ParsePythonFilter().call(Payload({"files": {"python": [path]}, "findings": [], "errors": []}))
    return AnalyzePrimitivesPerFileFilter().call(parsed).get("findings")


def test_flags_every_primitive_after_the_first(tmp_path):
    findings = analyze(_outside_tests(tmp_path, POSITIVE))
    assert by_line(findings) == expectations(POSITIVE)
    assert len(expectations(POSITIVE)) == 7


def test_one_primitive_with_its_helpers_is_clean(tmp_path):
    assert analyze(_outside_tests(tmp_path, NEGATIVE)) == []


def test_message_names_both_classes_and_the_fix(tmp_path):
    message = analyze(_outside_tests(tmp_path, POSITIVE))[0].message
    assert "SecondFilter" in message and "First" in message
    assert "own file" in message


def test_test_files_are_not_checked(tmp_path):
    assert analyze(_outside_tests(tmp_path, POSITIVE, "test_steps.py")) == []
    assert analyze(_outside_tests(tmp_path, POSITIVE, "tests/steps.py")) == []
    assert analyze(_outside_tests(tmp_path, POSITIVE, "pkg/tests/fixtures/steps.py")) == []
    assert analyze(_outside_tests(tmp_path, POSITIVE, "conftest.py")) == []
    assert analyze(POSITIVE) == []  # the fixture itself is under tests/


def test_suppression_comment_drops_the_finding(tmp_path):
    out = lint_paths([_outside_tests(tmp_path, SUPPRESSED)], disable=NAME_RULES)
    assert out.get("findings") == []
    assert len(out.get("suppressed")) == 1


def test_the_rule_runs_in_the_pipeline(tmp_path):
    out = lint_paths([_outside_tests(tmp_path, POSITIVE)], disable=NAME_RULES)
    assert {f.rule for f in out.get("findings")} == {"CUP-I005"}


def test_main_lists_the_rule(capsys):
    assert main(["--rules"]) == 0
    assert "CUP-I005  one-primitive-per-file" in capsys.readouterr().out
