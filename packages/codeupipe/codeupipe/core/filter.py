"""Filter protocol: sync by default, async by declaration.

New code should prefer ``Filter`` for CPU-bound transforms and opt into
``AsyncFilter`` (in ``async_filter.py``) when the step truly awaits I/O.

The runtime remains backward compatible with legacy async filters passed to
``Pipeline.add_filter()`` by detecting the coroutine signature at
registration time.
"""

from typing import Protocol, TypeVar

from .async_filter import AsyncFilter
from .payload import Payload

# AsyncFilter is re-exported for backward compatibility — it moved to
# async_filter.py under the one-component-per-file rule.
__all__ = ["Filter", "AsyncFilter"]

TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')


class Filter(Protocol[TInput, TOutput]):
    """Synchronous processing unit — takes a payload in, returns payload out."""

    def call(self, payload: Payload[TInput]) -> Payload[TOutput]:
        """Process the payload and return a transformed result."""
        ...
