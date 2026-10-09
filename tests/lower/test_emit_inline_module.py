"""``lowering="inline"``: one flattened ``run()`` for the whole pipeline.

The fastest static mode: steps unrolled and inlined, no framework allocations.
Measured before building it: per-step calls and per-insert dict copies each
cost ~15-20% on P1; only removing both reached hand-written speed.

The contract is still parity with the dynamic runtime. These tests pin the
shapes where inlining with in-place writes could quietly break it.
"""

import asyncio

import pytest

from codeupipe import Payload, Pipeline, Valve
from codeupipe.lower import build_export_pipeline_v2

from .fixtures import export_module_globals as g
from .fixtures import inline_shapes as s
from .fixtures import instance_config as c
from .fixtures import plane_b
from .test_export_pipeline import _write_and_import


def _export_inline(pipeline):
    result = asyncio.run(build_export_pipeline_v2(write=False).run_async(
        Payload({"pipeline": pipeline, "pattern": "flat", "lowering": "inline"})))
    return result.get("files") or []


def _pipeline(*steps):
    p = Pipeline()
    for name, step in steps:
        if hasattr(step, "observe"):
            p.add_tap(step)
        else:
            p.add_filter(step)
    return p


def _assert_parity(pipeline, package, inputs):
    for data in inputs:
        before = dict(data)
        assert package.run(dict(data)) == pipeline.run(Payload(dict(data))).to_dict(), data
        assert data == before


class TestInlineLayout:
    def test_emits_one_module_with_a_single_run_function(self):
        p = _pipeline(("uses_constant", g.UsesConstant()), ("uses_helper", g.UsesHelper()))
        p.add_filter(Valve(s.SetA(), s.AIsSet()))

        files = _export_inline(p)
        paths = sorted(f["path"].rsplit("/", 1)[-1] for f in files)
        module = next(f["content"] for f in files if f["path"].endswith("pipeline.py"))

        assert paths == ["__init__.py", "pipeline.py"]
        assert module.count("\ndef run(") == 1
        assert "def uses_constant" not in module
        assert "{**data" not in module

    def test_does_not_mutate_the_callers_input(self, tmp_path):
        p = _pipeline(("set_a", s.SetA()))
        package = _write_and_import(_export_inline(p), tmp_path)
        data = {"x": 1}

        package.run(data)

        assert data == {"x": 1}


class TestInlineParity:
    def test_module_globals_helpers_regex_and_taps(self, tmp_path):
        p = _pipeline(
            ("uses_constant", g.UsesConstant()),
            ("uses_transitive_constant", g.UsesTransitiveConstant()),
            ("uses_helper", g.UsesHelper()),
            ("uses_compiled_regex", g.UsesCompiledRegex()),
            ("uses_from_import_constant", g.UsesFromImportConstant()),
            ("records_to_module_list", g.RecordsToModuleList()),
        )
        package = _write_and_import(_export_inline(p), tmp_path)

        _assert_parity(p, package, [{"price": 10, "x": 4, "text": "ab 12 cd"}, {}, {"text": "zz"}])

    def test_two_instances_of_one_configured_filter_stay_distinct(self, tmp_path):
        p = _pipeline(("member", c.Discount(0.1)), ("clearance", c.Discount(0.5)), ("keep", c.KeepKeys(("price",))))
        package = _write_and_import(_export_inline(p), tmp_path)

        _assert_parity(p, package, [{"price": 100, "junk": 1}, {"price": 3}])

    def test_valve_gates_an_inlined_step(self, tmp_path):
        p = _pipeline(("set_a", s.SetA()))
        p.add_filter(Valve(s.ChainReadsOldValue(), s.AIsSet()))
        package = _write_and_import(_export_inline(p), tmp_path)

        _assert_parity(p, package, [{}, {"a": 5}])

    def test_a_multi_key_insert_reads_the_payload_from_before_the_chain(self, tmp_path):
        p = _pipeline(("set_a", s.SetA()), ("chain", s.ChainReadsOldValue()))
        package = _write_and_import(_export_inline(p), tmp_path)

        assert package.run({}) == {"a": 100, "b": 1}
        _assert_parity(p, package, [{}])

    def test_a_step_with_an_early_return_still_runs_correctly(self, tmp_path):
        p = _pipeline(("early", s.EarlyReturn()), ("set_a", s.SetA()))
        package = _write_and_import(_export_inline(p), tmp_path)

        _assert_parity(p, package, [{}, {"a": 1}, {"a": 0}])

    def test_a_stored_reference_does_not_see_later_in_place_writes(self, tmp_path):
        p = _pipeline(("keeps", s.KeepsReference()), ("tap", s.TapKeepsReference()), ("set_a", s.SetA()))
        package = _write_and_import(_export_inline(p), tmp_path)

        result = package.run({"x": 1})

        # The exported module carries its own copies of the fixture's lists
        # (step-prefixed), so read what *it* recorded.
        exported = vars(package.pipeline)
        kept = next(v for k, v in exported.items() if k.endswith("KEPT"))
        seen = next(v for k, v in exported.items() if k.endswith("SEEN_BY_TAP"))
        assert result == {"x": 1, "kept": True, "a": 1}
        assert kept == [{"x": 1}, {"x": 1}]
        assert seen == [{"x": 1, "kept": True}]


class TestInlinePlaneB:
    def test_a_failing_tap_does_not_halt_the_inlined_run(self, tmp_path):
        p = _pipeline(("score", plane_b.Score()), ("audit", plane_b.ExplodingTap()), ("set_a", s.SetA()))
        package = _write_and_import(_export_inline(p), tmp_path)

        _assert_parity(p, package, [{"x": 1}])

    def test_base_exceptions_still_propagate(self, tmp_path):
        p = _pipeline(("score", plane_b.Score()), ("audit", plane_b.Interrupting()))
        package = _write_and_import(_export_inline(p), tmp_path)

        with pytest.raises(KeyboardInterrupt):
            package.run({"x": 1})


def _inline_module(pipeline):
    return next(f["content"] for f in _export_inline(pipeline) if f["path"].endswith("pipeline.py"))


class TestInlineRemovesRedundantCopies:
    """A predicate that calls a one-line helper is inlined with no dict copy."""

    def test_a_one_line_helper_predicate_is_inlined_without_a_copy(self, tmp_path):
        p = Pipeline()
        p.add_filter(Valve(s.SetA(), s.ViaHelper()))
        module = _inline_module(p)

        condition = next(line for line in module.splitlines() if line.strip().startswith("if "))
        assert "dict(" not in condition
        package = _write_and_import(_export_inline(p), tmp_path)
        _assert_parity(p, package, [{"on": True}, {"on": 1}, {}])


class TestInlineContractVocabulary:
    def test_has_and_remove_inline_without_a_fallback_copy(self, tmp_path):
        p = _pipeline(("hr", s.HasAndRemove()))
        module = _inline_module(p)

        assert "def _hr__step" not in module  # inlined, not called on a copy
        package = _write_and_import(_export_inline(p), tmp_path)
        _assert_parity(p, package, [{"a": 1, "drop": 2}, {"drop": 1}, {}])
