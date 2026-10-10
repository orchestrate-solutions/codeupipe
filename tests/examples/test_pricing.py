"""The README example. Each primitive is in its own file, and the pipeline
file puts them together. It runs, a failing Tap does not halt it, and its
export gives the same answer with no framework import."""

import importlib.util
import pathlib
import subprocess
import sys

from codeupipe import Payload

from examples.pricing.at_least_predicate import AtLeastPredicate
from examples.pricing.discount_filter import DiscountFilter
from examples.pricing.mark_bulk_filter import MarkBulkFilter
from examples.pricing.pricing_pipeline import PricingPipeline
from examples.pricing.print_steps_hook import PrintStepsHook

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / "pricing"
PARTS = {"discount_filter.py": "DiscountFilter", "mark_bulk_filter.py": "MarkBulkFilter",
         "at_least_predicate.py": "AtLeastPredicate", "audit_tap.py": "AuditTap",
         "print_steps_hook.py": "PrintStepsHook"}


def test_each_primitive_is_alone_in_its_file():
    for name, cls in PARTS.items():
        source = (EXAMPLE / name).read_text()
        assert source.count("\nclass ") == 1 and f"\nclass {cls}" in source, name
        assert "Pipeline" not in source, f"{name} must not know the pipeline"


def test_the_pipeline_file_only_puts_them_together():
    source = (EXAMPLE / "pricing_pipeline.py").read_text()
    assert source.count("\nclass ") == 1 and "\nclass PricingPipeline(Pipeline):" in source
    assert "def call" not in source and "def test" not in source and "def observe" not in source
    for module in ("discount_filter", "mark_bulk_filter", "at_least_predicate", "audit_tap"):
        assert f"from .{module} import" in source


def test_each_part_works_alone():
    assert DiscountFilter(0.5).call(Payload({"price": 10.0})).to_dict() == {"price": 5.0}
    assert MarkBulkFilter().call(Payload({})).to_dict() == {"bulk": True}
    assert AtLeastPredicate("qty", 10).test(Payload({"qty": 10})) is True
    assert AtLeastPredicate("qty", 10).test(Payload({"qty": 9})) is False


def test_dynamic_run():
    pipeline = PricingPipeline()
    out = pipeline.run(Payload({"price": 100.0, "qty": 12}))
    assert out.to_dict() == {"price": 90.0, "qty": 12, "bulk": True}
    assert pipeline.labels == ["DiscountFilter",
                                   "MarkBulkFilter",
                                   "AuditTap"]
    assert [name for name, _ in pipeline.state.errors] == ["AuditTap"]


def test_valve_skips_small_orders():
    pipeline = PricingPipeline()
    out = pipeline.run(Payload({"price": 100.0, "qty": 2}))
    assert out.to_dict() == {"price": 90.0, "qty": 2}
    assert pipeline.state.skipped == ["MarkBulkFilter"]


def test_a_hook_sees_each_step(capsys):
    pipeline = PricingPipeline()
    pipeline.use_hook(PrintStepsHook())
    pipeline.run(Payload({"price": 100.0, "qty": 12}))
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["  DiscountFilter", "  MarkBulkFilter"]


def test_the_example_runs_as_a_module():
    done = subprocess.run([sys.executable, "-m", "examples.pricing"], capture_output=True, text=True,
                          cwd=EXAMPLE.parents[1])
    assert done.returncode == 0, done.stderr
    assert "{'price': 90.0, 'qty': 12, 'bulk': True}" in done.stdout


def test_export_matches_and_has_no_framework_import(tmp_path):
    done = subprocess.run(
        [sys.executable, "-m", "codeupipe.lower", "examples.pricing.pricing_pipeline:PricingPipeline", "--out", str(tmp_path)],
        capture_output=True, text=True, cwd=EXAMPLE.parents[1],
    )
    assert done.returncode == 0, done.stderr
    steps = tmp_path / "src" / "steps"
    for path in steps.glob("*.py"):
        assert "codeupipe" not in path.read_text()
    spec = importlib.util.spec_from_file_location(
        "exported_pricing", steps / "__init__.py", submodule_search_locations=[str(steps)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["exported_pricing"] = module
    try:
        spec.loader.exec_module(module)
        assert module.run({"price": 100.0, "qty": 12}) == {"price": 90.0, "qty": 12, "bulk": True}
    finally:
        for name in [n for n in sys.modules if n.startswith("exported_pricing")]:
            del sys.modules[name]
