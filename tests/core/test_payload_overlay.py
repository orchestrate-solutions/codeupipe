"""Payload's overlay engine must be indistinguishable from a copied dict.

Writes overlay a delta on the parent instead of copying,
so these pin the edges where an overlay could diverge from plain dict
semantics. They pass on the old copy-per-insert engine too: the engine is
an implementation detail, the behaviour is the contract.
"""

from codeupipe import Payload
from codeupipe.core import payload as payload_module


def _reference(ops):
    """The same operations on a plain dict."""
    d = {}
    for op, *args in ops:
        if op == "insert":
            d = {**d, args[0]: args[1]}
        elif op == "remove":
            d = {k: v for k, v in d.items() if k != args[0]}
    return d


def _apply(ops):
    p = Payload()
    for op, *args in ops:
        p = p.insert(*args) if op == "insert" else p.remove(*args)
    return p


def test_a_chain_far_past_the_flatten_depth_reads_correctly():
    depth = getattr(payload_module, "_FLATTEN_DEPTH", 32) * 3 + 5
    ops = [("insert", f"k{i % 7}", i) for i in range(depth)]
    p = _apply(ops)
    assert p.to_dict() == _reference(ops)
    assert all(p.get(f"k{i}") == _reference(ops)[f"k{i}"] for i in range(7))


def test_remove_then_reinsert_and_has():
    ops = [("insert", "a", 1), ("insert", "b", 2), ("remove", "a"), ("insert", "c", 3)]
    p = _apply(ops)
    assert not p.has("a") and p.get("a", "absent") == "absent"
    p2 = p.insert("a", None)
    assert p2.has("a") and p2.get("a", "absent") is None
    assert list(p2.to_dict()) == ["b", "c", "a"]  # dict insertion order


def test_overwrite_keeps_the_original_key_position():
    p = Payload({"a": 1, "b": 2}).insert("a", 9)
    assert list(p.to_dict().items()) == [("a", 9), ("b", 2)]


def test_every_ancestor_is_unchanged_by_later_writes():
    base = Payload({"a": 1})
    child = base.insert("b", 2)
    grandchild = child.remove("a").insert("c", 3)
    assert base.to_dict() == {"a": 1}
    assert child.to_dict() == {"a": 1, "b": 2}
    assert grandchild.to_dict() == {"b": 2, "c": 3}


def test_to_dict_is_a_copy_the_caller_may_change():
    p = Payload({"a": 1}).insert("b", 2)
    d = p.to_dict()
    d["zz"] = 1
    assert p.to_dict() == {"a": 1, "b": 2}


def test_the_callers_input_dict_is_never_shared():
    source = {"a": 1}
    p = Payload(source).insert("b", 2)
    source["a"] = 999
    assert p.get("a") == 1


def test_merge_right_side_wins_and_trace_lineage_carry():
    p = Payload({"a": 1, "b": 1}, trace_id="t").insert("x", 0)
    q = p.merge(Payload({"a": 2, "c": 3}))
    assert q.to_dict() == {"a": 2, "b": 1, "x": 0, "c": 3}
    assert q.trace_id == "t"


def test_with_trace_and_stamp_share_contents_without_changing_them():
    p = Payload({"a": 1}).insert("b", 2)
    traced = p.with_trace("t-1")._stamp("step")
    assert traced.to_dict() == p.to_dict()
    assert traced.trace_id == "t-1" and traced.lineage == ["step"]
    assert p.trace_id is None and p.lineage == []
