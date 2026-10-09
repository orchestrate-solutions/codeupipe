"""`python -m codeupipe.lower module:name --out DIR`: the export as a command."""

import importlib
import sys

import pytest

from codeupipe.core import Payload
from codeupipe.lower.__main__ import main
from tests.lower.fixtures import cli_targets

TARGETS = "tests.lower.fixtures.cli_targets"
INPUTS = [{"price": 100, "qty": 12}, {"price": 80, "qty": 2}, {}]


def load_export(out_dir):
    """Import the exported package from disk only, as a user would."""
    for name in [m for m in sys.modules if m == "steps" or m.startswith("steps.")]:
        del sys.modules[name]
    sys.path.insert(0, str(out_dir / "src"))
    try:
        return importlib.import_module("steps")
    finally:
        sys.path.remove(str(out_dir / "src"))


def test_exports_a_module_level_pipeline_that_matches_the_dynamic_run(tmp_path, capsys):
    out = tmp_path / "out"

    code = main([f"{TARGETS}:PRICING", "--out", str(out)])

    assert code == 0
    exported = load_export(out)
    for data in INPUTS:
        assert exported.run(dict(data)) == cli_targets.PRICING.run(Payload(dict(data))).to_dict()
    assert "src/steps/pipeline.py" in capsys.readouterr().out


def test_exports_what_a_builder_function_returns(tmp_path):
    out = tmp_path / "out"

    assert main([f"{TARGETS}:build_pricing", "--out", str(out)]) == 0

    assert load_export(out).run({"price": 100}) == {"price": 50.0}


def test_exports_a_named_pipeline_type(tmp_path):
    out = tmp_path / "out"

    assert main([f"{TARGETS}:Checkout", "--out", str(out)]) == 0

    assert load_export(out).run({"price": 100}) == {"price": 75.0}


def test_inline_lowering_writes_one_module_and_still_matches(tmp_path):
    out = tmp_path / "out"

    assert main([f"{TARGETS}:PRICING", "--out", str(out), "--lowering", "inline"]) == 0

    assert sorted(p.name for p in (out / "src" / "steps").iterdir()) == ["__init__.py", "pipeline.py"]
    exported = load_export(out)
    for data in INPUTS:
        assert exported.run(dict(data)) == cli_targets.PRICING.run(Payload(dict(data))).to_dict()


def test_observe_export_records_state(tmp_path):
    out = tmp_path / "out"

    assert main([f"{TARGETS}:PRICING", "--out", str(out), "--observe"]) == 0

    state = {}
    load_export(out).run({"price": 100, "qty": 1}, state=state)
    assert len(state["executed"]) == 2
    assert len(state["skipped"]) == 1


def test_a_refused_shape_exits_1_names_the_step_and_writes_nothing(tmp_path, capsys):
    out = tmp_path / "out"

    code = main([f"{TARGETS}:REFUSED", "--out", str(out)])

    assert code == 1
    assert "HoldsAnObject" in capsys.readouterr().err
    assert not out.exists()


def test_observe_with_inline_is_a_usage_error(tmp_path, capsys):
    out = tmp_path / "out"

    code = main([f"{TARGETS}:PRICING", "--out", str(out), "--lowering", "inline", "--observe"])

    assert code == 2
    assert "steps" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize("target, says", [
    ("no_colon_here", "module:name"),
    ("no.such.module:PRICING", "no.such.module"),
    (f"{TARGETS}:MISSING", "MISSING"),
    (f"{TARGETS}:NOT_A_PIPELINE", "not a Pipeline"),
    (f"{TARGETS}:needs_an_argument", "arguments"),
    (f"{TARGETS}:returns_something_else", "not a Pipeline"),
])
def test_a_bad_target_exits_2_and_says_why(tmp_path, capsys, target, says):
    out = tmp_path / "out"

    code = main([target, "--out", str(out)])

    assert code == 2
    assert says in capsys.readouterr().err
    assert not out.exists()


def test_refuses_a_non_empty_output_directory(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep.txt").write_text("mine")

    code = main([f"{TARGETS}:PRICING", "--out", str(out)])

    assert code == 2
    assert "not empty" in capsys.readouterr().err
    assert sorted(p.name for p in out.iterdir()) == ["keep.txt"]


def test_overwrite_writes_into_a_non_empty_directory_and_keeps_other_files(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep.txt").write_text("mine")

    assert main([f"{TARGETS}:PRICING", "--out", str(out), "--overwrite"]) == 0

    assert (out / "keep.txt").read_text() == "mine"
    assert load_export(out).run({"price": 100}) == {"price": 90.0}


def test_an_empty_existing_output_directory_is_fine(tmp_path):
    out = tmp_path / "out"
    out.mkdir()

    assert main([f"{TARGETS}:build_pricing", "--out", str(out)]) == 0


def test_runs_as_a_module(tmp_path):
    import subprocess

    out = tmp_path / "out"
    done = subprocess.run(
        [sys.executable, "-m", "codeupipe.lower", f"{TARGETS}:build_pricing", "--out", str(out)],
        capture_output=True, text=True,
    )

    assert done.returncode == 0, done.stderr
    assert (out / "src" / "steps" / "pipeline.py").is_file()
