"""RED tests for RewritePayloadOpsFilter (M0).

These tests describe the full rewrite table from
docs/plan/converter-v2/architecture.md. Every rule is a test.

Developer contract: make each test pass. When they're all green, the
export-side AST rewriter is done.
"""

import ast
import textwrap

import pytest

from codeupipe import Payload
from codeupipe.lower.errors import UnsupportedFilterShape
from codeupipe.lower.filters.rewrite_payload_ops import RewritePayloadOpsFilter
from codeupipe.lower.ir import PipelineIR, StepIR, PipelineMeta


def _fn(src: str) -> ast.FunctionDef:
    return ast.parse(textwrap.dedent(src)).body[0]  # type: ignore[return-value]


def _wrap(fn: ast.FunctionDef, name: str = "step", kind: str = "filter") -> PipelineIR:
    return PipelineIR(steps=[StepIR(name=name, kind=kind, call_ast=fn, source_hint=name)])


def _rewrite(ir: PipelineIR) -> PipelineIR:
    out = RewritePayloadOpsFilter().call(Payload({"pipeline_ir": ir}))
    return out.get("pipeline_ir")


def _unparse(step: StepIR) -> str:
    return ast.unparse(step.call_ast)


class TestGetRewrites:
    def test_payload_get_key_becomes_data_get_key(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.get("name")
            """
        )
        ir = _rewrite(_wrap(fn))
        src = _unparse(ir.steps[0])
        assert "payload" not in src
        assert 'data.get("name")' in src or "data.get('name')" in src

    def test_payload_get_key_with_default(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.get("name", "anon")
            """
        )
        ir = _rewrite(_wrap(fn))
        src = _unparse(ir.steps[0])
        assert "data.get" in src
        assert "'anon'" in src or '"anon"' in src


class TestInsertRewrites:
    def test_single_insert_becomes_dict_merge(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.insert("k", 1)
            """
        )
        ir = _rewrite(_wrap(fn))
        src = _unparse(ir.steps[0])
        assert "payload" not in src
        assert "**data" in src
        assert "1" in src

    def test_chained_insert_collapses_to_single_merge(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.insert("a", 1).insert("b", 2).insert("c", 3)
            """
        )
        ir = _rewrite(_wrap(fn))
        src = _unparse(ir.steps[0])
        # collapsed into ONE dict merge, not three nested calls
        assert src.count("**data") == 1
        assert "'a'" in src or '"a"' in src
        assert "'b'" in src or '"b"' in src
        assert "'c'" in src or '"c"' in src

    def test_insert_return_no_payload_leak(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.insert("k", payload.get("v"))
            """
        )
        ir = _rewrite(_wrap(fn))
        src = _unparse(ir.steps[0])
        assert "payload" not in src


class TestReturnRewrites:
    def test_bare_return_payload_becomes_return_data(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload
            """
        )
        ir = _rewrite(_wrap(fn))
        src = _unparse(ir.steps[0])
        assert "return data" in src
        assert "return payload" not in src


class TestSignatureRewrite:
    def test_call_self_payload_becomes_step_data(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload
            """
        )
        ir = _rewrite(_wrap(fn, name="clean_text"))
        src = _unparse(ir.steps[0])
        # exported function loses `self` and renames arg to `data`
        assert "def clean_text(data" in src
        assert "self" not in src.split("\n")[0]


class TestToDictRewrite:
    def test_to_dict_becomes_dict_data(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.to_dict()
            """
        )
        ir = _rewrite(_wrap(fn))
        src = _unparse(ir.steps[0])
        assert "dict(data)" in src


class TestFailureModes:
    def test_dynamic_key_lowers_to_a_computed_dict_key(self):
        # Was refused (M0 exportable subset). Plain Python evaluates a computed
        # key exactly as Payload.insert does, and configurable filters
        # (`payload.insert(self.key, ...)`) need it. Found by the conformance
        # suite: its reference `Set(key, value)` step could not be exported.
        fn = _fn(
            """
            def call(self, payload):
                key = "x"
                return payload.insert(key, 1)
            """
        )
        src = _unparse(_rewrite(_wrap(fn, name="Dyn")).steps[0])
        namespace = {}
        exec(src, namespace)  # noqa: S102 — rewritten test source
        assert namespace["Dyn"]({"a": 0}) == {"a": 0, "x": 1}

    def test_chained_dynamic_keys_that_collide_keep_the_last_value(self):
        fn = _fn(
            """
            def call(self, payload):
                first = "k"
                second = "k"
                return payload.insert(first, 1).insert(second, 2)
            """
        )
        src = _unparse(_rewrite(_wrap(fn, name="Dyn")).steps[0])
        namespace = {}
        exec(src, namespace)  # noqa: S102
        assert namespace["Dyn"]({}) == {"k": 2}

    def test_unknown_payload_method_raises(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.magic()
            """
        )
        with pytest.raises(UnsupportedFilterShape):
            _rewrite(_wrap(fn))


class TestValvePredicateRewrite:
    def test_predicate_is_also_rewritten(self):
        call_fn = _fn(
            """
            def call(self, payload):
                return payload.insert("gated", True)
            """
        )
        pred_fn = _fn(
            """
            def _pred(payload):
                return payload.get("tier") == "premium"
            """
        )
        ir = PipelineIR(
            steps=[StepIR(
                name="gate",
                kind="valve",
                call_ast=call_fn,
                predicate_ast=pred_fn,
                source_hint="gate",
            )]
        )
        out_ir = _rewrite(ir)
        pred_src = ast.unparse(out_ir.steps[0].predicate_ast)  # type: ignore[arg-type]
        assert "payload" not in pred_src
        assert "data.get" in pred_src


class TestContractVocabulary:
    """The API contract's Payload vocabulary lowers to plain dict operations
    (conformance/API.md): has, remove, merge, the Payload constructor, and
    the MutablePayload escape hatch."""

    def _run(self, src, data):
        out = _rewrite(_wrap(_fn(src), name="step"))
        code = ast.unparse(out.steps[0].call_ast)
        assert "payload" not in code and "Payload" not in code, code
        namespace = {}
        exec(code, namespace)  # noqa: S102 — rewritten test source
        before = dict(data)
        result = namespace["step"](data)
        assert data == before, "the lowered step mutated its input"
        return result

    def test_has_is_a_membership_test(self):
        src = """
            def call(self, payload):
                return payload.insert("has_a", payload.has("a"))
            """
        assert self._run(src, {"a": None}) == {"a": None, "has_a": True}
        assert self._run(src, {}) == {"has_a": False}

    def test_remove_drops_the_key_without_touching_the_input(self):
        src = """
            def call(self, payload):
                return payload.remove("x")
            """
        assert self._run(src, {"x": 1, "y": 2}) == {"y": 2}
        assert self._run(src, {"y": 2}) == {"y": 2}

    def test_merge_right_side_wins(self):
        src = """
            def call(self, payload):
                return payload.merge(Payload({"a": 2, "c": 3}))
            """
        assert self._run(src, {"a": 1, "b": 1}) == {"a": 2, "b": 1, "c": 3}

    def test_mutable_escape_hatch(self):
        src = """
            def call(self, payload):
                m = payload.with_mutation()
                m.set("k", "v")
                m.remove("drop")
                m.set("had_drop", m.has("drop"))
                return m.to_immutable()
            """
        assert self._run(src, {"drop": 1, "a": 1}) == {"a": 1, "k": "v", "had_drop": False}

    def test_an_operation_on_a_lowered_payload_is_lowered_too(self):
        src = """
            def call(self, payload):
                return payload.remove("drop").insert("had_a", payload.has("a"))
            """
        assert self._run(src, {"a": 1, "drop": 2}) == {"a": 1, "had_a": True}

    def test_a_non_payload_insert_is_left_alone(self):
        src = """
            def call(self, payload):
                items = [2]
                items.insert(0, 1)
                return payload.insert("items", items)
            """
        assert self._run(src, {}) == {"items": [1, 2]}
