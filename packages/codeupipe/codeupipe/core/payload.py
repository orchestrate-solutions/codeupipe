"""
Payload: the data that moves through a pipeline.

One keyed container. Every write changes it in place and returns it, so a
step can write and return in one line. ``copy()`` gives an independent
Payload when you want to keep the one you have.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

__all__ = ["Payload"]

T = TypeVar('T')


class Payload(Generic[T]):
    """Keyed data. Keys are strings; values are JSON-shaped.

    ``insert``, ``remove`` and ``merge`` change this Payload and return it.
    ``copy()`` returns a separate Payload with the same contents; writes to
    one do not reach the other. Values are shared, not deep-copied.
    """

    def __init__(self, data: Optional[Union[Dict[str, Any], T]] = None, *,
                 trace_id: Optional[str] = None, _lineage: Optional[List[str]] = None):
        if data is None:
            self._data: Dict[str, Any] = {}
        else:
            try:
                self._data = dict(data)  # type: ignore[arg-type]  # the caller's map is copied
            except (TypeError, ValueError):
                self._data = {}
        self._trace_id = trace_id
        self._lineage: List[str] = list(_lineage) if _lineage else []

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for key, or default if absent."""
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        """Whether ``key`` is present (even with a ``None`` value)."""
        return key in self._data

    def insert(self, key: str, value: Any) -> 'Payload[T]':
        """Set ``key`` to ``value`` in this Payload, and return it."""
        self._data[key] = value
        return self

    def remove(self, key: str) -> 'Payload[T]':
        """Remove ``key`` from this Payload (a no-op if it is absent), and return it."""
        self._data.pop(key, None)
        return self

    def merge(self, other: 'Payload[T]') -> 'Payload[T]':
        """Write every key of ``other`` into this Payload (``other`` wins), and return it."""
        self._data.update(other._data)
        self._trace_id = self._trace_id or other._trace_id
        self._lineage.extend(other._lineage)
        return self

    def copy(self) -> 'Payload[T]':
        """A separate Payload with the same contents, trace ID and lineage."""
        return Payload(self._data, trace_id=self._trace_id, _lineage=self._lineage)

    def to_dict(self) -> Dict[str, Any]:
        """The contents as a new dict."""
        return dict(self._data)

    @property
    def trace_id(self) -> Optional[str]:
        """Trace ID, for following one payload across systems."""
        return self._trace_id

    @property
    def lineage(self) -> List[str]:
        """The steps this payload has passed through, when lineage is on."""
        return list(self._lineage)

    def with_trace(self, trace_id: str) -> 'Payload[T]':
        """Set the trace ID on this Payload, and return it."""
        self._trace_id = trace_id
        return self

    def _stamp(self, step_name: str) -> 'Payload[T]':
        """Record a step in the lineage (internal)."""
        self._lineage.append(step_name)
        return self

    def __repr__(self) -> str:
        if self._trace_id:
            return f"Payload({self._data}, trace_id='{self._trace_id}')"
        return f"Payload({self._data})"
