from scorecard import vocab
from scorecard.snapshot_hook import SnapshotHook


def test_records_events_with_snapshots_for_dicts_and_payloads():
    hook = SnapshotHook()
    hook.before(None, {"a": 1})
    hook.after("s", vocab.Payload({"a": 2}))
    hook.on_error("s", RuntimeError("x"), {"a": 3})
    assert hook.sequence() == [("before", None, {"a": 1}, None), ("after", "s", {"a": 2}, None),
                               ("error", "s", {"a": 3}, "RuntimeError: x")]
    assert hook.mutated_after_the_fact() == []


def test_detects_a_payload_changed_after_it_was_seen():
    hook = SnapshotHook()
    data = {"a": 1}
    hook.after("s1", data)
    data["a"] = 2  # a later step writing in place into an earlier step's output
    assert hook.mutated_after_the_fact() == [(0, "after", "s1")]


def test_detects_a_nested_change():
    hook = SnapshotHook()
    data = {"a": [1]}
    hook.before("s1", data)
    data["a"].append(2)
    assert hook.mutated_after_the_fact() == [(0, "before", "s1")]
