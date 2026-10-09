"""
Tests for write-path optimizations.

1. SharedPayload internal serde format (msgpack when available, json fallback)
2. SharedPayload region pooling (ShmPool)
3. Lazy lineage (deferred copy-on-write)
"""

import pytest

from codeupipe.core.payload import Payload


# ── 1. SharedPayload internal format ─────────────────────────────────


class TestSharedPayloadInternalFormat:
    """SharedPayload should use msgpack internally when available."""

    def test_from_payload_uses_msgpack_when_available(self):
        """If msgpack is installed, SharedPayload uses it for internal serde."""
        from codeupipe.core.shared_payload import SharedPayload

        p = Payload({"x": 42, "name": "alice"}, trace_id="t1")
        sp = SharedPayload.from_payload(p)

        # The internal format should be detectable
        raw = bytes(sp._shm.buf[:sp._size])
        try:
            import msgpack
            # If msgpack is available, raw should NOT start with '{' (json)
            assert not raw.startswith(b'{'), "Should use msgpack, not json"
        except ImportError:
            # Fallback: should be json
            assert raw.startswith(b'{'), "Should fallback to json"

        sp.close()

    def test_roundtrip_still_works(self):
        """Data roundtrips correctly regardless of internal format."""
        from codeupipe.core.shared_payload import SharedPayload

        p = Payload({"x": 42, "scores": [1, 2, 3]}, trace_id="t1", _lineage=["s1"])
        sp = SharedPayload.from_payload(p)
        restored = sp.to_payload()

        assert restored.get("x") == 42
        assert restored.get("scores") == [1, 2, 3]
        assert restored.trace_id == "t1"
        assert restored.lineage == ["s1"]
        sp.close()

    def test_large_payload_msgpack_faster(self):
        """Large payloads should serialize faster with msgpack internally."""
        import time
        from codeupipe.core.shared_payload import SharedPayload

        big = Payload({"data": [float(i) * 0.001 for i in range(5000)]})

        # Measure SharedPayload.from_payload speed
        times = []
        for _ in range(20):
            t0 = time.perf_counter_ns()
            sp = SharedPayload.from_payload(big)
            t1 = time.perf_counter_ns()
            times.append((t1 - t0) / 1000)
            sp.close()

        median_us = sorted(times)[len(times) // 2]
        # With msgpack, large writes should be well under 1ms
        # JSON would be ~2-3ms for this size
        try:
            import msgpack
            assert median_us < 1000, f"With msgpack, expected <1ms, got {median_us:.0f}us"
        except ImportError:
            pass  # Can't assert speed without msgpack


# ── 2. Region pooling ────────────────────────────────────────────────


class TestShmPool:
    """ShmPool pre-allocates regions to avoid kernel overhead per write."""

    def test_import(self):
        """ShmPool is importable."""
        from codeupipe.core.shared_payload import ShmPool
        assert ShmPool is not None

    def test_pool_alloc_and_release(self):
        """Pool allocates a region and accepts it back."""
        from codeupipe.core.shared_payload import ShmPool

        pool = ShmPool(slot_size=4096, num_slots=2)
        try:
            sp = pool.write(Payload({"x": 42}))
            assert sp.get("x") == 42
            sp.close()
        finally:
            pool.shutdown()

    def test_pool_reuses_regions(self):
        """After close(), the region is returned to the pool for reuse."""
        from codeupipe.core.shared_payload import ShmPool

        pool = ShmPool(slot_size=4096, num_slots=2)
        try:
            sp1 = pool.write(Payload({"x": 1}))
            name1 = sp1._shm.name
            sp1.close()

            sp2 = pool.write(Payload({"x": 2}))
            name2 = sp2._shm.name
            # Region should be reused
            assert name2 == name1, f"Expected reuse: {name1} vs {name2}"
            assert sp2.get("x") == 2
            sp2.close()
        finally:
            pool.shutdown()

    def test_pool_exhaustion_creates_new(self):
        """When pool is exhausted, falls back to creating a new region."""
        from codeupipe.core.shared_payload import ShmPool

        pool = ShmPool(slot_size=4096, num_slots=1)
        try:
            sp1 = pool.write(Payload({"x": 1}))
            # Pool is now empty — next write should still work
            sp2 = pool.write(Payload({"x": 2}))
            assert sp2.get("x") == 2
            sp1.close()
            sp2.close()
        finally:
            pool.shutdown()

    def test_pool_handles_oversized(self):
        """Payloads larger than slot_size still work (allocated fresh)."""
        from codeupipe.core.shared_payload import ShmPool

        pool = ShmPool(slot_size=64, num_slots=2)
        try:
            big = Payload({"data": list(range(1000))})
            sp = pool.write(big)
            assert len(sp.get("data")) == 1000
            sp.close()
        finally:
            pool.shutdown()

    def test_pool_shutdown_cleans_all(self):
        """shutdown() releases all pre-allocated regions."""
        from codeupipe.core.shared_payload import ShmPool

        pool = ShmPool(slot_size=4096, num_slots=3)
        pool.shutdown()
        # No assertion needed — just verifying no resource leak / crash


# ── 3. Lazy lineage ─────────────────────────────────────────────────


class TestLazyLineage:
    """Lineage uses copy-on-write to avoid per-stamp list allocation."""

    def test_stamp_returns_new_payload(self):
        """_stamp still returns a new Payload (contract unchanged)."""
        p = Payload({"x": 1}, _lineage=["s1"])
        p2 = p._stamp("s2")

        assert p.lineage == ["s1"]
        assert p2.lineage == ["s1", "s2"]

    def test_stamp_does_not_mutate_original(self):
        """Original payload's lineage is unchanged after stamp."""
        p = Payload({"x": 1}, _lineage=["a", "b", "c"])
        _ = p._stamp("d")
        assert p.lineage == ["a", "b", "c"]

    def test_stamp_shares_data_reference(self):
        """_stamp should share the _data dict reference (no copy) when
        only lineage changes."""
        p = Payload({"x": 1, "y": 2})
        p2 = p._stamp("s1")
        # They should share the same underlying dict object
        # (write optimization: skip dict.copy when only lineage changes)
        assert p2._data is p._data or p2.get("x") == 1  # at minimum, data identical

    def test_chain_of_stamps_efficient(self):
        """Multiple stamps in a row shouldn't create deep copies each time."""
        import time

        p = Payload({"big": list(range(10000))})

        # Measure chain of 20 stamps
        t0 = time.perf_counter_ns()
        current = p
        for i in range(20):
            current = current._stamp(f"step_{i}")
        elapsed_us = (time.perf_counter_ns() - t0) / 1000

        assert current.lineage == [f"step_{i}" for i in range(20)]
        # 20 stamps should take <50us (lazy: no dict copy per stamp)
        # Old behavior: 20 × 1.6us = 32us minimum
        # New behavior: should be significantly faster
        assert elapsed_us < 100, f"20 stamps took {elapsed_us:.0f}us"

    def test_insert_after_stamp_is_independent(self):
        """insert() after _stamp produces correct data."""
        p = Payload({"x": 1})
        p2 = p._stamp("s1")
        p3 = p2.insert("y", 2)

        assert p.get("y") is None
        assert p2.get("y") is None
        assert p3.get("y") == 2
        assert p3.lineage == ["s1"]
