"""
Tests for AsyncTap

The async observation protocol, split out of tap.py under the
one-component-per-file rule. Taps observe and never modify — that contract is
what these tests pin.
"""

import asyncio
from typing import Protocol

import pytest

from codeupipe.core.async_tap import AsyncTap
from codeupipe.core.payload import Payload


class TestAsyncTapProtocol:
    @pytest.mark.unit
    @pytest.mark.core
    def test_async_tap_is_protocol(self):
        assert issubclass(AsyncTap, Protocol)

    @pytest.mark.unit
    @pytest.mark.core
    def test_reexported_from_tap_module(self):
        """`from codeupipe.core.tap import AsyncTap` must keep working."""
        from codeupipe.core.tap import AsyncTap as Reexported
        assert Reexported is AsyncTap

    @pytest.mark.unit
    @pytest.mark.core
    def test_exported_from_core(self):
        from codeupipe.core import AsyncTap as FromCore
        assert FromCore is AsyncTap


class RecordingTap:
    """Concrete AsyncTap for testing — records without modifying."""

    def __init__(self):
        self.seen = []

    async def observe(self, payload: Payload) -> None:
        self.seen.append(payload.get("value"))


class TestAsyncTapBehavior:
    @pytest.mark.unit
    @pytest.mark.core
    def test_async_tap_observes(self):
        tap = RecordingTap()
        asyncio.run(tap.observe(Payload({"value": 7})))
        assert tap.seen == [7]

    @pytest.mark.unit
    @pytest.mark.core
    def test_async_tap_does_not_modify_payload(self):
        payload = Payload({"value": 7})
        asyncio.run(RecordingTap().observe(payload))
        assert payload.to_dict() == {"value": 7}

    @pytest.mark.unit
    @pytest.mark.core
    def test_observe_returns_none(self):
        """A Tap that returned data would be a Filter."""
        assert asyncio.run(RecordingTap().observe(Payload({"value": 1}))) is None
