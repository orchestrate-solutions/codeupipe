"""Hook: sees the lifecycle of a run."""

from abc import ABC
from typing import Optional, TypeVar
from .payload import Payload

__all__ = ["Hook"]

T = TypeVar('T')


class Hook(ABC):
    """Lifecycle hook for pipeline execution."""

    def before(self, step: Optional[str], payload: Payload[T]) -> None:
        """Before step ``step`` (its name), or before the pipeline starts (``None``)."""
        pass

    def after(self, step: Optional[str], payload: Payload[T]) -> None:
        """After step ``step`` (its name), or after the pipeline ends (``None``)."""
        pass

    def on_error(self, step: Optional[str], error: Exception, payload: Payload[T]) -> None:
        """Called when an error occurs."""
        pass
