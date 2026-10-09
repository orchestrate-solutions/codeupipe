from scorecard import vocab
from scorecard.snapshot_hook import SnapshotHook


def test_records_events_with_snapshots_for_dicts_and_payloads():
    hook = SnapshotHook()
    hook.before(None, {"a": 1})
    hook.after("s", vocab.Payload({"a": 2}))
    hook.on_error("s", RuntimeError("x"), {"a": 3})
    assert hook.sequence() == [("before", None, {"a": 1}, None), ("after", "s", {"a": 2}, None),
                               ("error", "s", {"a": 3}, "RuntimeError: x")]


def test_a_snapshot_keeps_the_value_at_the_event():
    hook = SnapshotHook()
    data = {"a": [1]}
    hook.before("s1", data)
    data["a"].append(2)  # a later in-place write
    data["b"] = 3
    assert hook.sequence() == [("before", "s1", {"a": [1]}, None)]
