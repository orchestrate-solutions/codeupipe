"""Payload: one keyed container. Writes are in place; copy() separates."""

from codeupipe import Payload


class TestConstruct:
    def test_empty(self):
        assert Payload().to_dict() == {}
        assert Payload(None).to_dict() == {}

    def test_the_callers_map_is_copied(self):
        data = {"a": 1}
        payload = Payload(data)
        payload.insert("b", 2)
        assert data == {"a": 1}


class TestRead:
    def test_get(self):
        payload = Payload({"a": 1, "zero": 0, "none": None})
        assert payload.get("a") == 1
        assert payload.get("zero") == 0
        assert payload.get("missing") is None
        assert payload.get("missing", "default") == "default"
        assert payload.get("none", "default") is None

    def test_has_reports_presence_even_for_none(self):
        payload = Payload({"none": None})
        assert payload.has("none") is True
        assert payload.has("missing") is False

    def test_to_dict_is_a_new_dict(self):
        payload = Payload({"a": 1})
        out = payload.to_dict()
        out["a"] = 2
        assert payload.get("a") == 1


class TestWritesAreInPlace:
    def test_insert_changes_this_payload_and_returns_it(self):
        payload = Payload({"a": 1})
        assert payload.insert("b", 2) is payload
        assert payload.to_dict() == {"a": 1, "b": 2}

    def test_remove_changes_this_payload_and_returns_it(self):
        payload = Payload({"a": 1, "b": 2})
        assert payload.remove("a") is payload
        assert payload.remove("missing") is payload
        assert payload.to_dict() == {"b": 2}

    def test_merge_writes_the_other_side_over_this_one(self):
        payload = Payload({"a": 1, "b": 1})
        other = Payload({"a": 2, "c": 3})
        assert payload.merge(other) is payload
        assert payload.to_dict() == {"a": 2, "b": 1, "c": 3}
        assert other.to_dict() == {"a": 2, "c": 3}

    def test_writes_chain(self):
        payload = Payload({})
        payload.insert("a", 1).insert("b", payload.get("a")).remove("a")
        assert payload.to_dict() == {"b": 1}


class TestCopy:
    def test_a_copy_is_separate(self):
        payload = Payload({"a": 1})
        copy = payload.copy()
        copy.insert("a", 2)
        payload.insert("b", 3)
        assert payload.to_dict() == {"a": 1, "b": 3}
        assert copy.to_dict() == {"a": 2}

    def test_a_copy_keeps_trace_and_lineage(self):
        payload = Payload({"a": 1}).with_trace("t-1")
        payload._stamp("step")
        copy = payload.copy()
        copy._stamp("later")
        assert copy.trace_id == "t-1"
        assert copy.lineage == ["step", "later"]
        assert payload.lineage == ["step"]

    def test_values_are_shared_not_deep_copied(self):
        items = [1]
        payload = Payload({"items": items})
        assert payload.copy().get("items") is items


class TestTrace:
    def test_with_trace_sets_it_on_this_payload(self):
        payload = Payload({"a": 1})
        assert payload.trace_id is None
        assert payload.with_trace("t-1") is payload
        assert payload.trace_id == "t-1"

    def test_lineage_is_read_as_a_copy(self):
        payload = Payload({})
        payload._stamp("s1")
        payload.lineage.append("not recorded")
        assert payload.lineage == ["s1"]

    def test_merge_keeps_this_trace_and_adds_the_other_lineage(self):
        left = Payload({}).with_trace("left")
        left._stamp("l")
        right = Payload({}).with_trace("right")
        right._stamp("r")
        left.merge(right)
        assert left.trace_id == "left"
        assert left.lineage == ["l", "r"]


def test_repr():
    assert repr(Payload({"a": 1})) == "Payload({'a': 1})"
    assert repr(Payload({"a": 1}).with_trace("t")) == "Payload({'a': 1}, trace_id='t')"
