"""Export bakes a filter's constructor config into the lowered step.

Export lowers a *live* Pipeline, so every ``self.<attr>`` a step reads is
already known: that is compile-time information, and static mode should
compile it in. Before this, ``Discount(rate=0.25)`` exported as a function
that read an undefined ``self`` — NameError at run time, success at export.
"""

import asyncio

import pytest

from codeupipe import Payload, Pipeline
from codeupipe.compile import build_export_pipeline_v2
from codeupipe.compile.errors import UnsupportedFilterShape

from .fixtures import instance_config as c
from .test_export_pipeline import _write_and_import


def _export(pipeline):
    result = asyncio.run(build_export_pipeline_v2(write=False).run_async(
        Payload({"pipeline": pipeline, "pattern": "flat"})))
    return result.get("files") or []


class TestConstructorConfigIsBakedIn:
    def test_two_instances_of_one_filter_keep_their_own_config(self, tmp_path):
        p = Pipeline()
        p.add_filter(c.Discount(0.1))
        p.add_filter(c.Discount(0.5))
        dynamic = p.run(Payload({"price": 100})).to_dict()

        package = _write_and_import(_export(p), tmp_path)

        assert package.run({"price": 100}) == dynamic == {"price": 45.0}

    def test_container_and_none_config_values_round_trip(self, tmp_path):
        p = Pipeline()
        p.add_filter(c.KeepKeys(("a", "b")))
        dynamic = p.run(Payload({"a": 1, "b": 2, "c": 3})).to_dict()

        package = _write_and_import(_export(p), tmp_path)

        assert package.run({"a": 1, "b": 2, "c": 3}) == dynamic == {"a": 1, "b": 2, "label": None}

    def test_tap_config_is_baked_in_too(self, tmp_path):
        p = Pipeline()
        p.add_tap(c.Tagger({"seen": True}))

        package = _write_and_import(_export(p), tmp_path)

        assert package.run({"x": 1}) == {"x": 1}

    def test_no_emitted_step_refers_to_self(self):
        p = Pipeline()
        p.add_filter(c.Discount(0.25))

        step = next(f["content"] for f in _export(p) if f["path"].endswith("discount.py"))

        assert "self" not in step.replace("_self_", "")


class TestConfigThatCannotBeCompiledInIsRefused:
    @pytest.mark.parametrize("filter_, attribute", [
        (c.HoldsAnObject(), "client"),
        (c.CountsCalls(), "count"),
        (c.UsesAHelperMethod(), "_double"),
    ])
    def test_refused_at_export_naming_the_attribute(self, filter_, attribute):
        p = Pipeline()
        p.add_filter(filter_)

        with pytest.raises(UnsupportedFilterShape) as info:
            _export(p)

        assert attribute in str(info.value)


class TestPredicateConfigIsBakedIn:
    """Predicates are objects; export compiles their literal settings in,
    as for filters, and keeps them apart from the filter's own settings."""

    @pytest.mark.parametrize("lowering", ["steps", "inline"])
    def test_a_configured_predicate_exports_like_the_dynamic_run(self, tmp_path, lowering):

        pipeline = Pipeline()
        # the filter's self.key ("flag") and the predicate's self.key ("n") differ
        pipeline.add_valve(c.AtLeast("n", 5), c.SetFlag("flag"))
        out = build_export_pipeline_v2(write=False).run(
            Payload({"pipeline": pipeline, "pattern": "flat", "lowering": lowering}))
        package = _write_and_import(out.get("files"), tmp_path)
        for n in (1, 5, 9):
            assert package.run({"n": n}) == pipeline.run(Payload({"n": n})).to_dict()
        assert package.run({"n": 5}) == {"n": 5, "flag": True}
