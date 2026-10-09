"""RewritePayloadOpsFilter: every Payload operation and its plain-dict form."""

import ast
import textwrap

import pytest

from codeupipe import Payload
from codeupipe.lower.errors import UnsupportedFilterShape
from codeupipe.lower.filters.rewrite_payload_ops_filter import RewritePayloadOpsFilter
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
    def test_single_insert_becomes_an_assignment(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.insert("k", 1)
            """
        )
        ir = _rewrite(_wrap(fn))
        src = _unparse(ir.steps[0])
        assert "payload" not in src
        assert "data['k'] = 1" in src
        assert src.rstrip().endswith("return data")

    def test_chained_inserts_become_assignments_in_order(self):
        fn = _fn(
            """
            def call(self, payload):
                return payload.insert("a", 1).insert("b", 2).insert("c", 3)
            """
        )
        ir = _rewrite(_wrap(fn))
        body = [line.strip() for line in _unparse(ir.steps[0]).splitlines()[1:]]
        assert body == ["data['a'] = 1", "data['b'] = 2", "data['c'] = 3", "return data"]

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
    """The contract's Payload vocabulary lowers to plain dict operations
    (conformance/API.md). A write changes the dict it is given, as a Payload
    write changes the Payload; the exported run() makes the one copy."""

    def _code(self, src, kind="filter"):
        out = _rewrite(_wrap(_fn(src), name="step", kind=kind))
        code = ast.unparse(out.steps[0].call_ast)
        assert "payload" not in code and "Payload" not in code, code
        return code

    def _run(self, src, data):
        namespace = {}
        exec(self._code(src), namespace)  # noqa: S102 — rewritten test source
        return namespace["step"](dict(data))

    def test_has_is_a_membership_test(self):
        src = """
            def call(self, payload):
                return payload.insert("has_a", payload.has("a"))
            """
        assert self._run(src, {"a": None}) == {"a": None, "has_a": True}
        assert self._run(src, {}) == {"has_a": False}

    def test_remove_drops_the_key(self):
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

    def test_a_write_as_a_statement_changes_the_payload(self):
        src = """
            def call(self, payload):
                payload.insert("k", "v")
                payload.remove("drop")
                payload.insert("had_drop", payload.has("drop"))
                return payload
            """
        assert self._run(src, {"drop": 1, "a": 1}) == {"a": 1, "k": "v", "had_drop": False}

    def test_a_later_link_of_a_chain_reads_the_earlier_write(self):
        src = """
            def call(self, payload):
                return payload.remove("drop").insert("had_drop", payload.has("drop")).insert("a2", payload.get("a"))
            """
        assert self._run(src, {"a": 1, "drop": 2}) == {"a": 1, "had_drop": False, "a2": 1}

    def test_a_second_name_for_the_payload_is_the_same_payload(self):
        src = """
            def call(self, payload):
                out = payload
                out = out.remove("drop")
                out.insert("seen", payload.has("drop"))
                return out
            """
        assert self._run(src, {"drop": 1}) == {"seen": False}

    def test_copy_gives_a_separate_payload(self):
        src = """
            def call(self, payload):
                before = payload.copy()
                payload.insert("a", 2)
                return payload.insert("was", before.get("a"))
            """
        assert self._run(src, {"a": 1}) == {"a": 2, "was": 1}

    def test_a_copy_can_be_written_and_returned(self):
        src = """
            def call(self, payload):
                return payload.copy().insert("a", 2)
            """
        data = {"a": 1}
        namespace = {}
        exec(self._code(src), namespace)  # noqa: S102 — rewritten test source
        assert namespace["step"](data) == {"a": 2}
        assert data == {"a": 1}

    def test_a_non_payload_insert_is_left_alone(self):
        src = """
            def call(self, payload):
                items = [2]
                items.insert(0, 1)
                return payload.insert("items", items)
            """
        assert self._run(src, {}) == {"items": [1, 2]}

    @pytest.mark.parametrize("line", [
        'return [payload.insert("a", 1)]',
        'return payload.insert("a", 1).get("a")',
        'return payload.insert("a", 1) if payload.has("b") else payload',
        'print(payload.merge(Payload({"a": 1})))',
    ])
    def test_a_write_inside_a_larger_expression_is_refused(self, line):
        src = f"""
            def call(self, payload):
                {line}
            """
        with pytest.raises(UnsupportedFilterShape, match="statement of its own"):
            self._code(src)

    def test_a_tap_that_writes_is_refused(self):
        src = """
            def observe(self, payload):
                payload.insert("seen", True)
            """
        with pytest.raises(UnsupportedFilterShape, match="Tap or a predicate"):
            self._code(src, kind="tap")
