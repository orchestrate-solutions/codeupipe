"""AsyncFilter protocol — the processing unit that explicitly awaits.

Split from ``filter.py`` to satisfy the one-component-per-file rule (CUP001).
``Filter`` remains the default; reach for this only when a step truly awaits
I/O rather than doing CPU-bound work.

``filter.py`` re-exports this name, so ``from codeupipe.core.filter import
AsyncFilter`` keeps working.
"""

from typing import Protocol, TypeVar

from .payload import Payload

__all__ = ["AsyncFilter"]

TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')


class AsyncFilter(Protocol[TInput, TOutput]):
    """Async processing unit — explicitly opts into suspension."""

    async def call(self, payload: Payload[TInput]) -> Payload[TOutput]:
        """Process the payload and return a transformed result."""
        ...
