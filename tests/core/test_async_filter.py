"""
Tests for AsyncFilter

The async processing protocol, split out of filter.py under the
one-component-per-file rule. These tests also pin the backward-compatible
re-export, since existing code imports AsyncFilter from either location.
"""

import asyncio
from typing import Protocol

import pytest

from codeupipe.core.async_filter import AsyncFilter
from codeupipe.core.payload import Payload


class TestAsyncFilterProtocol:
    @pytest.mark.unit
    @pytest.mark.core
    def test_async_filter_is_protocol(self):
        assert issubclass(AsyncFilter, Protocol)

    @pytest.mark.unit
    @pytest.mark.core
    def test_reexported_from_filter_module(self):
        """`from codeupipe.core.filter import AsyncFilter` must keep working."""
        from codeupipe.core.filter import AsyncFilter as Reexported
        assert Reexported is AsyncFilter

    @pytest.mark.unit
    @pytest.mark.core
    def test_exported_from_core(self):
        from codeupipe.core import AsyncFilter as FromCore
        assert FromCore is AsyncFilter


class DoublingFilter:
    """Concrete AsyncFilter for testing."""

    async def call(self, payload: Payload) -> Payload:
        return payload.insert("value", payload.get("value") * 2)


class TestAsyncFilterBehavior:
    @pytest.mark.unit
    @pytest.mark.core
    def test_async_filter_transforms_payload(self):
        result = asyncio.run(DoublingFilter().call(Payload({"value": 21})))
        assert result.get("value") == 42

    @pytest.mark.unit
    @pytest.mark.core
    def test_async_filter_writes_in_place_and_returns_the_payload(self):
        original = Payload({"value": 1})
        result = asyncio.run(DoublingFilter().call(original))
        assert result is original
        assert result.get("value") == 2

    @pytest.mark.unit
    @pytest.mark.core
    def test_structural_conformance(self):
        """A class with an async `call` satisfies the protocol structurally."""
        assert asyncio.iscoroutinefunction(DoublingFilter().call)
