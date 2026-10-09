"""
Tests for SharedPayload — mmap-backed zero-copy Payload for same-machine hops.

SharedPayload uses shared memory (mmap) to eliminate serialization entirely.
The producer writes structured data to a memory region; the consumer reads
it directly via a handle. For ML model training, large tensor metadata,
and high-throughput same-machine pipelines.
"""

import pytest

from codeupipe.core.payload import Payload


# ── Unit: SharedPayload lifecycle ────────────────────────────────────


class TestSharedPayloadBasic:
    """Tier 1 — create, read, close SharedPayload."""

    def test_import(self):
        """SharedPayload is importable from codeupipe.core."""
        from codeupipe.core.shared_payload import SharedPayload
        assert SharedPayload is not None

    def test_create_from_payload(self):
        """Convert a regular Payload into SharedPayload."""
        from codeupipe.core.shared_payload import SharedPayload

        p = Payload({"x": 42, "name": "alice"}, trace_id="t1")
        sp = SharedPayload.from_payload(p)

        assert sp.get("x") == 42
        assert sp.get("name") == "alice"
        assert sp.trace_id == "t1"
        sp.close()

    def test_to_payload(self):
        """Convert SharedPayload back to a regular Payload."""
        from codeupipe.core.shared_payload import SharedPayload

        p = Payload({"x": 42}, trace_id="t1", _lineage=["s1"])
        sp = SharedPayload.from_payload(p)
        restored = sp.to_payload()

        assert isinstance(restored, Payload)
        assert restored.get("x") == 42
        assert restored.trace_id == "t1"
        assert restored.lineage == ["s1"]
        sp.close()

    def test_lineage_preserved(self):
        """Lineage survives the roundtrip."""
        from codeupipe.core.shared_payload import SharedPayload

        p = Payload({"a": 1}, _lineage=["step1", "step2"])
        sp = SharedPayload.from_payload(p)
        assert sp.lineage == ["step1", "step2"]
        sp.close()


# ── Unit: Handle-based transfer ──────────────────────────────────────


class TestSharedPayloadHandle:
    """Transfer SharedPayload between processes via handle."""

    def test_handle_roundtrip(self):
        """Get a handle, reconstruct from handle — same data."""
        from codeupipe.core.shared_payload import SharedPayload

        p = Payload({"score": 99.5, "model": "resnet50"}, trace_id="train-1")
        sp = SharedPayload.from_payload(p)
        handle = sp.handle()

        # Simulate consumer side — reconstruct from handle
        sp2 = SharedPayload.from_handle(handle)
        assert sp2.get("score") == 99.5
        assert sp2.get("model") == "resnet50"
        assert sp2.trace_id == "train-1"

        sp.close()
        sp2.close()

    def test_handle_is_small(self):
        """Handle is a lightweight reference, not the full data."""
        from codeupipe.core.shared_payload import SharedPayload

        large_data = {"big_list": list(range(10000))}
        p = Payload(large_data)
        sp = SharedPayload.from_payload(p)
        handle = sp.handle()

        # Handle should be much smaller than the data itself
        import json
        data_size = len(json.dumps(large_data))
        handle_size = len(json.dumps(handle)) if isinstance(handle, dict) else len(str(handle))
        assert handle_size < data_size / 10, f"Handle {handle_size} should be << data {data_size}"

        sp.close()

    def test_handle_contains_name(self):
        """Handle contains the shared memory name for cross-process use."""
        from codeupipe.core.shared_payload import SharedPayload

        sp = SharedPayload.from_payload(Payload({"x": 1}))
        handle = sp.handle()

        assert "name" in handle
        assert "size" in handle
        sp.close()


# ── Unit: Payload.serialize(fmt="shm") integration ──────────────────


class TestShmFormat:
    """Verify fmt='shm' works through Payload's serialize/deserialize API."""

    def test_serialize_returns_handle_bytes(self):
        """serialize(fmt='shm') returns bytes encoding the handle, not the data."""
        from codeupipe.core.shared_payload import SharedPayload

        p = Payload({"x": 42}, trace_id="t1")
        raw = p.serialize(fmt="shm")
        assert isinstance(raw, bytes)

        # Deserialize should reconstruct the payload
        restored = Payload.deserialize(raw, fmt="shm")
        assert restored.get("x") == 42
        assert restored.trace_id == "t1"

    def test_shm_much_smaller_wire_size(self):
        """Wire bytes for shm are just the handle — much smaller than data."""
        large_data = {"values": list(range(5000))}
        p = Payload(large_data)

        json_size = len(p.serialize(fmt="json"))
        shm_size = len(p.serialize(fmt="shm"))

        assert shm_size < json_size / 5, f"shm={shm_size} should be << json={json_size}"


# ── Unit: Cleanup ────────────────────────────────────────────────────


class TestSharedPayloadCleanup:
    """Shared memory regions are properly cleaned up."""

    def test_close_releases_memory(self):
        """After close(), the memory region is released."""
        from codeupipe.core.shared_payload import SharedPayload

        sp = SharedPayload.from_payload(Payload({"x": 1}))
        handle = sp.handle()
        sp.close()

        # Attempting to open the same region should fail
        with pytest.raises(Exception):
            SharedPayload.from_handle(handle)

    def test_context_manager(self):
        """SharedPayload works as a context manager for auto-cleanup."""
        from codeupipe.core.shared_payload import SharedPayload

        with SharedPayload.from_payload(Payload({"x": 1})) as sp:
            assert sp.get("x") == 1
            handle = sp.handle()

        # After exit, region should be cleaned up
        with pytest.raises(Exception):
            SharedPayload.from_handle(handle)


# ── Integration: Large payload (ML-scale) ────────────────────────────


class TestSharedPayloadLarge:
    """Verify SharedPayload handles ML-scale data sizes."""

    def test_large_payload_roundtrip(self):
        """1 MB payload survives shared memory roundtrip."""
        from codeupipe.core.shared_payload import SharedPayload

        # 1 MB of float values (simulating tensor metadata)
        big_list = [float(i) * 0.001 for i in range(50000)]
        p = Payload({"tensor_meta": big_list, "shape": [100, 500]})
        sp = SharedPayload.from_payload(p)
        handle = sp.handle()

        sp2 = SharedPayload.from_handle(handle)
        assert len(sp2.get("tensor_meta")) == 50000
        assert sp2.get("shape") == [100, 500]

        sp.close()
        sp2.close()
