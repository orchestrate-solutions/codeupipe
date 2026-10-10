"""The export erases a step's type hints: exported code needs no framework."""

import subprocess
import sys

import pytest

from codeupipe.core import Payload
from codeupipe.compile.__main__ import main
from tests.compile.fixtures import typed_steps

TARGET = "tests.compile.fixtures.typed_steps:build"
INPUTS = [{"price": 2.5, "qty": 2}, {"price": 1.0, "qty": 12}]
MODES = [[], ["--lowering", "inline"], ["--observe"]]


def exported_text(out):
    return {str(path.relative_to(out)): path.read_text() for path in sorted(out.rglob("*.py"))}


@pytest.mark.parametrize("mode", MODES, ids=["steps", "inline", "observe"])
def test_no_type_or_framework_name_reaches_the_output(tmp_path, mode):
    out = tmp_path / "out"

    assert main([TARGET, "--out", str(out)] + mode) == 0

    for name, text in exported_text(out).items():
        for unwanted in ("codeupipe", "Payload", "TypedDict", "Order", "Totalled", "Flagged", "typing",
                         "List", "Optional"):
            assert unwanted not in text, "%s still mentions %s:\n%s" % (name, unwanted, text)


@pytest.mark.parametrize("mode", MODES, ids=["steps", "inline", "observe"])
def test_the_output_runs_where_the_framework_is_not_installed(tmp_path, mode):
    out = tmp_path / "out"
    assert main([TARGET, "--out", str(out)] + mode) == 0

    for data in INPUTS:
        # -I and an explicit path: nothing of this repo is importable in the child.
        script = "import sys; sys.path.insert(0, %r); import steps; print(steps.run(%r))" % (str(out / "src"), data)
        done = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, cwd=tmp_path)

        assert done.returncode == 0, done.stderr
        assert eval(done.stdout) == typed_steps.build().run(Payload(dict(data))).to_dict()


def test_an_annotated_local_keeps_its_value_and_loses_its_type(tmp_path):
    out = tmp_path / "out"
    assert main([TARGET, "--out", str(out), "--lowering", "inline"]) == 0
    text = (out / "src" / "steps" / "pipeline.py").read_text()

    assert "lines = [" in text
    assert "note" not in text


def test_erasing_hints_never_leaves_an_empty_block():
    import ast

    from codeupipe.compile.filters.parse_filter_source_filter import _erase_annotations

    source = (
        "def call(self, payload: 'P', *rest: int, flag: bool = False, **more: str) -> 'P':\n"
        "    if flag:\n"
        "        note: str\n"
        "    count: int = 0\n"
        "    return payload\n"
    )
    erased = ast.unparse(_erase_annotations(ast.parse(source).body[0]))

    assert erased == (
        "def call(self, payload, *rest, flag=False, **more):\n"
        "    if flag:\n"
        "        pass\n"
        "    count = 0\n"
        "    return payload"
    )
    compile(erased, "<erased>", "exec")
