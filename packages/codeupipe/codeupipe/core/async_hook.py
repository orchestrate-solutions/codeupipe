"""AsyncHook: a Hook whose methods are coroutines."""

from typing import Optional, TypeVar

from .hook import Hook
from .payload import Payload

__all__ = ["AsyncHook"]

T = TypeVar('T')


class AsyncHook(Hook):
    """Lifecycle hook that explicitly opts into async suspension."""

    async def before(self, step: Optional[str], payload: Payload[T]) -> None:
        """Before step ``step`` (its name), or before the pipeline starts (``None``)."""
        pass

    async def after(self, step: Optional[str], payload: Payload[T]) -> None:
        """After step ``step`` (its name), or after the pipeline ends (``None``)."""
        pass

    async def on_error(self, step: Optional[str], error: Exception, payload: Payload[T]) -> None:
        """Called when an error occurs."""
        pass
