"""Export carries a filter's own module-level names into the emitted package.

Constants and helpers defined next to a filter must not be dropped, and a
compiled regex must not be imported as ``from re import <NAME>``.
"""

import asyncio

import pytest

from codeupipe import Payload, Pipeline
from codeupipe.lower import build_export_pipeline_v2
from codeupipe.lower.errors import UnsupportedFilterShape

from .fixtures import export_module_globals as g
from .test_export_pipeline import _write_and_import


def _export(pipeline):
    result = asyncio.run(build_export_pipeline_v2(write=False).run_async(
        Payload({"pipeline": pipeline, "pattern": "flat"})))
    return result.get("files") or []


def _pipeline(*steps):
    p = Pipeline()
    for name, step in steps:
        if hasattr(step, "observe"):
            p.add_tap(step)
        else:
            p.add_filter(step)
    return p


class TestModuleLevelNamesSurviveExport:
    def test_exported_package_runs_with_module_constants_helpers_and_regex(self, tmp_path):
        pipeline = _pipeline(
            ("uses_constant", g.UsesConstant()),
            ("uses_transitive_constant", g.UsesTransitiveConstant()),
            ("uses_helper", g.UsesHelper()),
            ("uses_compiled_regex", g.UsesCompiledRegex()),
            ("uses_from_import_constant", g.UsesFromImportConstant()),
            ("records_to_module_list", g.RecordsToModuleList()),
        )
        dynamic = pipeline.run(Payload({"price": 10, "x": 4, "text": "ab 12 cd"})).to_dict()

        package = _write_and_import(_export(pipeline), tmp_path)
        exported = package.run({"price": 10, "x": 4, "text": "ab 12 cd"})

        assert exported == dynamic

    def test_compiled_regex_is_defined_not_imported_from_re(self):
        files = _export(_pipeline(("uses_compiled_regex", g.UsesCompiledRegex())))
        step = next(f["content"] for f in files if f["path"].endswith("uses_compiled_regex.py"))

        assert "from re import _WORDS" not in step
        assert "import re as _re" in step
        assert "_WORDS = _re.compile" in step

    def test_constants_only_travel_to_the_step_that_uses_them(self):
        files = _export(_pipeline(
            ("uses_constant", g.UsesConstant()),
            ("uses_helper", g.UsesHelper()),
        ))
        by_step = {f["path"].rsplit("/", 1)[-1]: f["content"] for f in files}

        # generated module names: step_<n>_<snake of the filter class>
        assert "_RATE = 0.5" in by_step["step_01_uses_constant.py"]
        assert "_RATE" not in by_step["step_02_uses_helper.py"]
        assert "def _double" in by_step["step_02_uses_helper.py"]

    def test_name_with_no_source_definition_fails_loud(self):
        with pytest.raises(UnsupportedFilterShape) as info:
            _export(_pipeline(("uses_injected", g.UsesInjected())))

        assert "_INJECTED" in str(info.value)
