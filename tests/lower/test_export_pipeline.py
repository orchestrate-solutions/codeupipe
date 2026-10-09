"""M1 EXIT test — end-to-end export path against a synthetic pipeline.

Success = a real CUP Pipeline of two Filters exports to a folder in memory
whose orchestrator, when exec-ed, reproduces the CUP output.
"""

import asyncio
import ast
import textwrap

import pytest

from codeupipe import Payload, Pipeline
from codeupipe.lower import build_export_pipeline_v2


class SubPipeline(Pipeline):
    """A named pipeline type, so it can be nested (conformance/API.md, step identity)."""


class _CleanText:
    def call(self, payload):
        return payload.insert("text", payload.get("text", "").strip())


class _AddGreeting:
    def call(self, payload):
        return payload.insert("greeting", "hello " + payload.get("text", ""))


@pytest.mark.slow
class TestExportPipelineEndToEnd:
    def _cup_output(self, input_data):
        p = Pipeline()
        p.add_filter(_CleanText())
        p.add_filter(_AddGreeting())
        return asyncio.run(p.run_async(Payload(input_data))).to_dict()

    def test_exported_orchestrator_matches_cup(self, tmp_path):
        source = Pipeline()
        source.add_filter(_CleanText())
        source.add_filter(_AddGreeting())
        exp = build_export_pipeline_v2(write=False)
        result = asyncio.run(exp.run_async(Payload({
            "pipeline": source,
            "pattern": "flat",
        })))
        files = result.get("files") or []
        assert files, "exporter must emit files"
        # No CUP leak anywhere in the emitted package.
        for f in files:
            for framework in ("codeupipe", "codeupipe"):
                assert framework not in f["content"], f"{framework} leak in {f['path']}"
        package = _write_and_import(files, tmp_path)
        run_fn = getattr(package, "run", None)
        assert run_fn is not None, "exported package must expose `run`"
        got = run_fn({"text": "  world  "})
        want = self._cup_output({"text": "  world  "})
        assert got == want


def _write_and_import(files, root):
    """Write the exported files to ``root`` and import them as a customer would.

    Deliberately NOT the shared-namespace ``exec`` used above: that pattern
    makes every step visible to the orchestrator whether or not it imports
    them, which hid a package that could not be imported from disk at all.
    """
    import importlib
    import sys

    for f in files:
        target = root / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"])
    package_parent = str(root / "src")
    for name in [m for m in sys.modules if m == "steps" or m.startswith("steps.")]:
        del sys.modules[name]
    sys.path.insert(0, package_parent)
    try:
        return importlib.import_module("steps")
    finally:
        sys.path.remove(package_parent)


class TestExportedPackageLoadsFromDisk:
    def test_exported_package_imports_and_runs_from_disk(self, tmp_path):
        source = Pipeline()
        source.add_filter(_CleanText())
        source.add_filter(_AddGreeting())
        result = asyncio.run(build_export_pipeline_v2(write=False).run_async(
            Payload({"pipeline": source, "pattern": "flat"})))

        package = _write_and_import(result.get("files") or [], tmp_path)

        assert package.run({"text": "  world  "}) == {"text": "world", "greeting": "hello world"}


class _Discount:
    def call(self, payload):
        return payload.insert("price", payload.get("price", 0) - 1)


class _IsMember:

    def test(self, payload):
        return payload.get('member') is True


class _IsMemberShortName:

    def test(self, p):
        return p.get('member') is True


def _export_files(pipeline):
    result = asyncio.run(build_export_pipeline_v2(write=False).run_async(
        Payload({"pipeline": pipeline, "pattern": "flat"})))
    return result.get("files") or []


class TestValvePredicateExport:
    def _pipeline(self, predicate):

        p = Pipeline()
        p.add_filter(_CleanText())
        p.add_valve(predicate, _Discount())
        return p

    def test_valve_gates_exported_step_like_dynamic_run(self, tmp_path):
        package = _write_and_import(_export_files(self._pipeline(_IsMember())), tmp_path)

        assert package.run({"text": "a", "price": 10, "member": True})["price"] == 9
        assert package.run({"text": "a", "price": 10, "member": False})["price"] == 10
        assert package.run({"text": "a", "price": 10})["price"] == 10

    def test_predicate_parameter_need_not_be_named_payload(self, tmp_path):
        package = _write_and_import(_export_files(self._pipeline(_IsMemberShortName())), tmp_path)

        assert package.run({"text": "a", "price": 10, "member": True})["price"] == 9
        assert package.run({"text": "a", "price": 10, "member": False})["price"] == 10

    def test_lambda_predicate_is_refused_before_export(self):
        """Anonymous predicates never reach export: the Valve refuses them."""
        from codeupipe import AnonymousStep

        with pytest.raises(AnonymousStep, match="lambda"):
            self._pipeline(lambda payload: payload.get("member") is True)


class TestExportedTapIsolation:
    """Plane B in static mode: the lowered code must contain a Tap failure
    exactly as the dynamic runtime does, or the two modes diverge."""

    def _pipeline(self, tap):
        from .fixtures import plane_b

        p = Pipeline()
        p.add_filter(plane_b.Score())
        p.add_tap(tap)
        return p

    def test_a_failing_tap_does_not_halt_the_exported_run(self, tmp_path):
        from .fixtures import plane_b

        pipeline = self._pipeline(plane_b.ExplodingTap())
        dynamic = pipeline.run(Payload({"x": 1})).to_dict()

        package = _write_and_import(_export_files(pipeline), tmp_path)

        assert package.run({"x": 1}) == dynamic == {"x": 1, "score": 2}

    def test_base_exceptions_from_a_tap_still_propagate(self, tmp_path):
        from .fixtures import plane_b

        package = _write_and_import(_export_files(self._pipeline(plane_b.Interrupting())), tmp_path)

        with pytest.raises(KeyboardInterrupt):
            package.run({"x": 1})


class TestNestedPipelineExport:
    """A nested Pipeline lowers by flattening its steps into the parent
    (conformance: pipeline/nested-pipeline-is-a-step). Generated modules are
    numbered in flattened order; identities stay labels."""

    def test_nested_pipeline_exports_and_matches_dynamic(self, tmp_path):
        inner = SubPipeline()
        inner.add_filter(_AddGreeting())
        outer = Pipeline()
        outer.add_filter(_CleanText())
        outer.add_pipeline(inner)

        package = _write_and_import(_export_files(outer), tmp_path)

        data = {"text": "  world  "}
        assert package.run(dict(data)) == outer.run(Payload(dict(data))).to_dict()

    def test_flattened_steps_get_generated_module_names(self):
        inner = SubPipeline()
        inner.add_filter(_AddGreeting())
        outer = Pipeline()
        outer.add_filter(_CleanText())
        outer.add_pipeline(inner)

        paths = {f["path"].rsplit("/", 1)[-1] for f in _export_files(outer)}
        assert {"step_01_clean_text.py", "step_02_add_greeting.py"} <= paths
