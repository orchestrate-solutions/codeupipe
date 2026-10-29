import importlib
import json
import os
import subprocess
import sys

import pytest

from codeupipe import Payload
from codeupipe_add.__main__ import main

LAYOUT = """\
lang: python
root: src/pricing
components:
  - kind: filter
    name: Discount
    description: Takes a rate off the price.
  - kind: predicate
    name: AtLeast
  - kind: filter
    name: MarkBulk
  - kind: tap
    name: Audit
  - kind: hook
    name: PrintSteps
  - kind: pipeline
    name: Pricing
    steps:
      - Discount
      - valve: [AtLeast, MarkBulk]
      - Audit
    hooks:
      - PrintSteps
"""

MADE = ["src/pricing/discount_filter.py", "tests/test_discount_filter.py",
        "src/pricing/at_least_predicate.py", "tests/test_at_least_predicate.py",
        "src/pricing/mark_bulk_filter.py", "tests/test_mark_bulk_filter.py",
        "src/pricing/audit_tap.py", "tests/test_audit_tap.py",
        "src/pricing/print_steps_hook.py", "tests/test_print_steps_hook.py",
        "src/pricing/pricing_pipeline.py", "tests/test_pricing_pipeline.py"]


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "cup.layout.yaml").write_text(LAYOUT)
    return tmp_path


def test_the_layout_makes_each_component_and_its_test_in_order(project, capsys):
    assert main(["--layout", "cup.layout.yaml"]) == 0
    assert capsys.readouterr().out.splitlines() == MADE


def test_what_the_layout_makes_passes_the_linter_and_each_test_fails_at_red(project):
    main(["--layout", "cup.layout.yaml"])
    for lint_args in (["codeupipe_lint.invariants", "--strict"], ["codeupipe_lint.anonymous_steps"]):
        lint = subprocess.run([sys.executable, "-m", *lint_args, "src"], capture_output=True, text=True)
        assert lint.returncode == 0, lint.stdout + lint.stderr
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
                           capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(project)})
    assert "6 failed" in tests.stdout, tests.stdout
    assert tests.stdout.count("Write the acceptance case for") >= 6


def test_the_pipeline_that_the_layout_makes_runs(project, monkeypatch):
    main(["--layout", "cup.layout.yaml"])
    monkeypatch.syspath_prepend(str(project))
    pipeline = importlib.import_module("src.pricing.pricing_pipeline").PricingPipeline()
    assert pipeline.run(Payload({"price": 100.0})).to_dict() == {"price": 100.0}
    assert pipeline.state.executed == ["DiscountFilter", "AuditTap"]
    assert pipeline.state.skipped == ["MarkBulkFilter"]


def test_a_layout_that_grows_keeps_each_file_that_exists_and_says_so(project, capsys):
    main(["--layout", "cup.layout.yaml"])
    capsys.readouterr()
    (project / "cup.layout.yaml").write_text(LAYOUT + "  - kind: filter\n    name: Rebate\n")
    assert main(["--layout", "cup.layout.yaml"]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == ["src/pricing/rebate_filter.py", "tests/test_rebate_filter.py"]
    assert "src/pricing/discount_filter.py exists, kept" in err.splitlines()


def test_a_layout_in_json_works_too(project, capsys):
    (project / "cup.layout.json").write_text(json.dumps({"lang": "python", "components": [
        {"kind": "filter", "name": "Discount"}]}))
    assert main(["--layout", "cup.layout.json"]) == 0
    assert capsys.readouterr().out.splitlines() == ["discount_filter.py", "tests/test_discount_filter.py"]


@pytest.mark.parametrize("argv", [
    ["filter", "Discount", "--layout", "cup.layout.yaml"],
    ["--layout", "cup.layout.yaml", "--description", "Takes a rate."],
    [],
    ["filter"],
])
def test_layout_with_the_arguments_of_phase_1_or_neither_is_refused_with_exit_2(project, capsys, argv):
    with pytest.raises(SystemExit) as stopped:
        main(argv)
    assert stopped.value.code == 2
    assert sorted(os.listdir(project)) == ["cup.layout.yaml"]


def test_a_layout_that_breaks_a_rule_writes_nothing(project, capsys):
    (project / "cup.layout.yaml").write_text(LAYOUT.replace("- Audit", "- Rebate"))
    assert main(["--layout", "cup.layout.yaml"]) == 2
    assert "Rebate" in capsys.readouterr().err
    assert sorted(os.listdir(project)) == ["cup.layout.yaml"]


def test_an_option_is_never_read_from_its_first_letters(project, capsys):
    with pytest.raises(SystemExit) as stopped:
        main(["filter", "Discount", "--desc", "Takes a rate."])
    assert stopped.value.code == 2
    assert sorted(os.listdir(project)) == ["cup.layout.yaml"]
