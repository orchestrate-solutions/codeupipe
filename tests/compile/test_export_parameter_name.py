"""A step may call its Payload parameter what it likes (``order``, ``p``).
The export follows that name: the compiled code gives the same output as the
dynamic run, and a refusal names the parameter as the author wrote it."""

import subprocess
import sys

import pytest

from codeupipe.compile.__main__ import main
from codeupipe.core import Payload
from tests.compile.fixtures import parameter_names

TARGET = "tests.compile.fixtures.parameter_names:build"
INPUTS = [{"price": 100.0, "qty": 12}, {"price": 19.99, "qty": 2}, {}]
MODES = [[], ["--lowering", "inline"], ["--observe"]]


@pytest.mark.parametrize("mode", MODES, ids=["steps", "inline", "observe"])
def test_the_compiled_code_gives_the_same_output(tmp_path, mode):
    out = tmp_path / "out"
    assert main([TARGET, "--out", str(out)] + mode) == 0

    for data in INPUTS:
        script = "import sys; sys.path.insert(0, %r); import steps; print(steps.run(%r))" % (str(out / "src"), data)
        done = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, cwd=tmp_path)

        assert done.returncode == 0, done.stderr
        assert eval(done.stdout) == parameter_names.build().run(Payload(dict(data))).to_dict()


class _WritesAnAttribute:
    def call(self, order):
        order.price = 1
        return order


class _ReadsAnAttribute:
    def call(self, order):
        return order.insert("price", order.price)


@pytest.mark.parametrize("step", [_WritesAnAttribute, _ReadsAnAttribute])
@pytest.mark.parametrize("lowering", ["steps", "inline"])
def test_an_attribute_of_the_parameter_is_refused_by_its_own_name(step, lowering):
    from codeupipe import Pipeline
    from codeupipe.compile import build_export_pipeline_v2
    from codeupipe.compile.errors import UnsupportedFilterShape

    pipeline = Pipeline()
    pipeline.add_filter(step())
    with pytest.raises(UnsupportedFilterShape) as refused:
        build_export_pipeline_v2().run(Payload({"pipeline": pipeline, "pattern": "flat", "lowering": lowering}))
    assert "order.price" in str(refused.value)
    assert step.__name__ in str(refused.value)
