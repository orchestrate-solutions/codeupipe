"""Tap protocol: sync by default, async by declaration.

``AsyncTap`` lives in ``async_tap.py`` under the one-component-per-file rule.
"""

from typing import Protocol, TypeVar

from .async_tap import AsyncTap
from .payload import Payload

# AsyncTap is re-exported for backward compatibility.
__all__ = ["Tap", "AsyncTap"]

T = TypeVar('T')


class Tap(Protocol[T]):
    """Synchronous observation point — inspect payload without changing it."""

    def observe(self, payload: Payload[T]) -> None:
        """Observe the payload. Must not modify it."""
        ...
