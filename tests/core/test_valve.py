"""
Tests for Valve

Testing conditional flow control with Valve.
"""

import pytest
import asyncio
from codeupipe.core.payload import Payload
from codeupipe.core.valve import Valve


class InnerFilter:

    async def call(self, payload):
        return payload.insert('ran', True)

class InnerFilter2:

    async def call(self, payload):
        return payload.insert('ran', True)

class InnerFilter3:

    async def call(self, payload):
        return payload.insert('processed', True)

class Dummy:

    async def call(self, payload):
        return payload

class Dummy2:

    async def call(self, payload):
        return payload

class _Predicate:

    def test(self, p):
        return True

class _Predicate2:

    def test(self, p):
        return False

class _Predicate3:

    def test(self, p):
        return (p.get('age') or 0) >= 18

class _Predicate4:

    def test(self, p):
        return True

class _Predicate5:

    def test(self, p):
        return True


class TestValve:
    """Test the Valve condtional flow control."""

    @pytest.mark.unit
    @pytest.mark.core
    def test_valve_passes_when_true(self):
        """Test that Valve executes inner filter when predicate is True."""


        valve = Valve(InnerFilter(), _Predicate())

        async def run_test():
            result = await valve.call(Payload())
            assert result.get("ran") is True

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_valve_blocks_when_false(self):
        """Test that Valve passes through unchanged when predicate is False."""


        valve = Valve(InnerFilter2(), _Predicate2())

        async def run_test():
            payload = Payload({"original": "data"})
            result = await valve.call(payload)
            assert result.get("ran") is None
            assert result.get("original") == "data"

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_valve_predicate_uses_payload(self):
        """Test that Valve predicate receives the payload."""


        valve = Valve(InnerFilter3(), _Predicate3())

        async def run_test():
            # Should pass
            result = await valve.call(Payload({"age": 20}))
            assert result.get("processed") is True

            # Should block
            result = await valve.call(Payload({"age": 15}))
            assert result.get("processed") is None

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_valve_repr(self):
        """Test Valve string representation."""


        valve = Valve(Dummy(), _Predicate4())
        assert "Dummy" in repr(valve) and "_Predicate4" in repr(valve)

    @pytest.mark.unit
    @pytest.mark.core
    def test_valve_conforms_to_filter_protocol(self):
        """Test that Valve has the same call() interface as Filter."""

        valve = Valve(Dummy2(), _Predicate5())
        assert hasattr(valve, 'call')
        assert callable(valve.call)
