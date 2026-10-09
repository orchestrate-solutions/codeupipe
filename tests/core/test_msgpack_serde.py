"""
Tests for msgpack serialization format on Payload.

Verifies that Payload.serialize(fmt="msgpack") and Payload.deserialize(raw, fmt="msgpack")
produce the same envelope contract as JSON but with better performance.
"""

import pytest

pytest.importorskip("msgpack", reason="msgpack not installed")

from codeupipe.core.payload import Payload


# ── Unit: Roundtrip ──────────────────────────────────────────────────


class TestMsgpackRoundtrip:
    """Tier 1 — isolated msgpack serialize/deserialize."""

    def test_basic_roundtrip(self):
        """Simple dict survives msgpack roundtrip."""
        p = Payload({"x": 42, "name": "alice"})
        raw = p.serialize(fmt="msgpack")
        restored = Payload.deserialize(raw, fmt="msgpack")
        assert restored.get("x") == 42
        assert restored.get("name") == "alice"

    def test_trace_id_preserved(self):
        """trace_id survives roundtrip."""
        p = Payload({"a": 1}, trace_id="trace-abc")
        raw = p.serialize(fmt="msgpack")
        restored = Payload.deserialize(raw, fmt="msgpack")
        assert restored.trace_id == "trace-abc"

    def test_lineage_preserved(self):
        """lineage list survives roundtrip."""
        p = Payload({"a": 1}, _lineage=["step1", "step2"])
        raw = p.serialize(fmt="msgpack")
        restored = Payload.deserialize(raw, fmt="msgpack")
        assert restored.lineage == ["step1", "step2"]

    def test_empty_payload(self):
        """Empty data dict roundtrips cleanly."""
        p = Payload()
        raw = p.serialize(fmt="msgpack")
        restored = Payload.deserialize(raw, fmt="msgpack")
        assert restored.to_dict() == {}
        assert restored.trace_id is None
        assert restored.lineage == []

    def test_nested_structures(self):
        """Nested dicts and lists survive roundtrip."""
        data = {
            "users": [{"id": 1, "name": "bob"}, {"id": 2, "name": "carol"}],
            "meta": {"page": 1, "total": 42},
        }
        p = Payload(data)
        raw = p.serialize(fmt="msgpack")
        restored = Payload.deserialize(raw, fmt="msgpack")
        assert restored.get("users") == data["users"]
        assert restored.get("meta") == data["meta"]

    def test_returns_bytes(self):
        """serialize(fmt='msgpack') returns bytes, not str."""
        p = Payload({"x": 1})
        raw = p.serialize(fmt="msgpack")
        assert isinstance(raw, bytes)

    def test_smaller_than_json(self):
        """msgpack wire size is smaller than JSON for same payload."""
        p = Payload({"user_id": 12345, "email": "test@example.com", "active": True})
        json_bytes = p.serialize(fmt="json")
        msgpack_bytes = p.serialize(fmt="msgpack")
        assert len(msgpack_bytes) < len(json_bytes)

    def test_all_json_types(self):
        """All JSON-representable types roundtrip correctly."""
        data = {
            "string": "hello",
            "integer": 42,
            "float": 3.14,
            "bool_true": True,
            "bool_false": False,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"a": "b"},
        }
        p = Payload(data, trace_id="t1", _lineage=["s1"])
        raw = p.serialize(fmt="msgpack")
        restored = Payload.deserialize(raw, fmt="msgpack")
        for key, value in data.items():
            assert restored.get(key) == value, f"Mismatch for key '{key}'"
        assert restored.trace_id == "t1"
        assert restored.lineage == ["s1"]


# ── Unit: Error Handling ─────────────────────────────────────────────


class TestMsgpackErrors:
    """Graceful handling when msgpack is not available or data is bad."""

    def test_bad_bytes_raises(self):
        """Non-msgpack bytes raise a meaningful error."""
        with pytest.raises(Exception):
            Payload.deserialize(b"not valid msgpack", fmt="msgpack")

    def test_missing_data_key(self):
        """Envelope without 'data' key gets empty dict."""
        import msgpack
        raw = msgpack.packb({"trace_id": "t1"})
        restored = Payload.deserialize(raw, fmt="msgpack")
        assert restored.to_dict() == {}
        assert restored.trace_id == "t1"


# ── Unit: Cross-format compatibility ────────────────────────────────


class TestCrossFormat:
    """Verify JSON and msgpack produce equivalent Payloads."""

    def test_json_to_msgpack_equivalence(self):
        """Deserializing from either format produces identical Payload state."""
        original = Payload({"x": 42, "y": "hello"}, trace_id="t1", _lineage=["s1"])

        from_json = Payload.deserialize(original.serialize(fmt="json"), fmt="json")
        from_msgpack = Payload.deserialize(original.serialize(fmt="msgpack"), fmt="msgpack")

        assert from_json.to_dict() == from_msgpack.to_dict()
        assert from_json.trace_id == from_msgpack.trace_id
        assert from_json.lineage == from_msgpack.lineage
