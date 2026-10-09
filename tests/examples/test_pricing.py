"""The README example: it runs, a failing Tap does not halt it, and its
export gives the same answer with no framework import."""

import importlib.util
import subprocess
import sys

from codeupipe import Payload

from examples.pricing import build_pricing


def test_dynamic_run():
    pipeline = build_pricing()
    out = pipeline.run(Payload({"price": 100.0, "qty": 12}))
    assert out.to_dict() == {"price": 90.0, "qty": 12, "bulk": True}
    assert [name for name, _ in pipeline.state.errors] == ["examples.pricing.AuditTap"]


def test_valve_skips_small_orders():
    out = build_pricing().run(Payload({"price": 100.0, "qty": 2}))
    assert out.to_dict() == {"price": 90.0, "qty": 2}


def test_export_matches_and_has_no_framework_import(tmp_path):
    done = subprocess.run(
        [sys.executable, "-m", "codeupipe.lower", "examples.pricing:build_pricing", "--out", str(tmp_path)],
        capture_output=True, text=True,
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
