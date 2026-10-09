"""AsyncTap protocol — the observation point that explicitly awaits.

Split from ``tap.py`` to satisfy the one-component-per-file rule (CUP001).
Like every Tap it must not modify the payload, and it must not raise into the
pipeline it observes.

``tap.py`` re-exports this name, so ``from codeupipe.core.tap import AsyncTap``
keeps working.
"""

from typing import Protocol, TypeVar

from .payload import Payload

__all__ = ["AsyncTap"]

T = TypeVar('T')


class AsyncTap(Protocol[T]):
    """Async observation point — explicitly opts into suspension."""

    async def observe(self, payload: Payload[T]) -> None:
        """Observe the payload. Must not modify it."""
        ...
