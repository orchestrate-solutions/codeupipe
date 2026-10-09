"""RED tests for EmitPlainFilesFilter (M1)."""

import ast
import textwrap

from codeupipe import Payload
from codeupipe.lower.filters.emit_plain_files import EmitPlainFilesFilter
from codeupipe.lower.ir import PipelineIR, StepIR


def _plain_fn(name: str) -> ast.FunctionDef:
    return ast.parse(textwrap.dedent(f"""
        def {name}(data):
            return {{**data, "seen": True}}
    """)).body[0]  # type: ignore[return-value]


def _ir(*names):
    return PipelineIR(steps=[
        StepIR(name=n, kind="filter", call_ast=_plain_fn(n), source_hint=n)
        for n in names
    ])


class TestEmitPlainFiles:
    def test_one_file_per_step(self):
        result = EmitPlainFilesFilter().call(Payload({
            "pipeline_ir": _ir("clean", "validate"),
            "config": {"pattern": "flat", "output": {"base": "src/", "step": "steps/"}},
        }))
        files = result.get("files") or []
        step_files = [f for f in files if "pipeline.py" not in f["path"]]
        assert len(step_files) == 2

    def test_no_codeupipe_imports_leak(self):
        result = EmitPlainFilesFilter().call(Payload({
            "pipeline_ir": _ir("clean"),
            "config": {"pattern": "flat", "output": {"base": "src/", "step": "steps/"}},
        }))
        for f in result.get("files") or []:
            for framework in ("codeupipe", "codeupipe"):
                assert framework not in f["content"], f"{framework} leak in {f['path']}"

    def test_deterministic_output(self):
        payload = {
            "pipeline_ir": _ir("a", "b", "c"),
            "config": {"pattern": "flat", "output": {"base": "src/", "step": "steps/"}},
        }
        r1 = EmitPlainFilesFilter().call(Payload(payload)).get("files")
        r2 = EmitPlainFilesFilter().call(Payload(payload)).get("files")
        assert r1 == r2


class TestPredicateNameCollision:
    """A copied helper may already own ``<step>_predicate`` — the name the
    orchestrator calls. Generated code has exactly this shape: a dict
    predicate ``<step>_predicate(data)`` wrapped by a Payload adapter."""

    def test_copied_helper_is_renamed_so_the_valve_predicate_does_not_call_itself(self):
        call = ast.parse("def gate(data):\n    return data\n").body[0]
        predicate = ast.parse("def gate(data):\n    return gate_predicate(dict(data))\n").body[0]
        step = StepIR(
            name="gate", kind="valve", call_ast=call, predicate_ast=predicate, source_hint="Gate",
            definitions=("def gate_predicate(data):\n    return data.get('on', False)",),
        )
        result = EmitPlainFilesFilter().call(Payload({"pipeline_ir": PipelineIR(steps=[step]), "files": []}))
        content = next(f["content"] for f in result.get("files") if f["path"].endswith("gate.py"))

        namespace = {}
        exec(content, namespace)  # noqa: S102 — emitted test source

        assert namespace["gate_predicate"]({"on": True}) is True
        assert namespace["gate_predicate"]({}) is False
