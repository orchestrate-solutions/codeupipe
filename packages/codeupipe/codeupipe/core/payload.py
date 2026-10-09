"""
Payload: The Data Container

The Payload carries data through the pipeline — immutable by default for safety,
mutable when flexibility is needed.
Enhanced with generic typing for type-safe workflows.
"""

import json
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union

__all__ = ["Payload", "MutablePayload"]

T = TypeVar('T')
TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')


_MISSING = object()

# Reads walk the chain of overlays, so it is flattened once it gets this deep:
# writes stay O(1) and a read is bounded by this many dict probes.
_FLATTEN_DEPTH = 32


class Payload(Generic[T]):
    """
    Immutable data container — holds data flowing through the pipeline.

    Writes (``insert``, ``remove``, ``merge``) never copy the whole dict: each
    returns a new Payload that overlays a small delta on its parent, so N inserts cost O(N) instead of O(N^2). Reads walk the
    overlays; the chain is flattened every ``_FLATTEN_DEPTH`` writes, and the
    flat view is cached. Values are shared, not copied, exactly as before.
    """

    def __init__(self, data: Optional[Union[Dict[str, Any], T]] = None, *,
                 trace_id: Optional[str] = None, _lineage: Optional[List[str]] = None):
        if data is None:
            root: Dict[str, Any] = {}
        elif isinstance(data, dict):
            root = data.copy() if data else {}
        else:
            try:
                root = dict(data)  # type: ignore
            except (TypeError, ValueError):
                root = {}
        self._init_root(root, trace_id, list(_lineage) if _lineage else [])

    def _init_root(self, root: Dict[str, Any], trace_id: Optional[str], lineage: List[str]) -> None:
        self._parent: Optional['Payload'] = None
        self._updates: Dict[str, Any] = root   # owned; never mutated after this
        self._removed: tuple = ()
        self._depth = 0
        self._cache: Optional[Dict[str, Any]] = root
        self._trace_id = trace_id
        self._lineage = lineage

    @classmethod
    def _from_parts(
        cls,
        data: Dict[str, Any],
        *,
        trace_id: Optional[str] = None,
        _lineage: Optional[List[str]] = None,
    ) -> 'Payload[T]':
        """Construct a Payload from already-owned data without cloning again."""
        payload = cls.__new__(cls)
        payload._init_root(data, trace_id, list(_lineage) if _lineage else [])
        return payload

    def _child(self, updates: Dict[str, Any], removed: tuple,
               trace_id: Any = _MISSING, lineage: Any = _MISSING) -> 'Payload[T]':
        child = Payload.__new__(Payload)
        child._trace_id = self._trace_id if trace_id is _MISSING else trace_id
        child._lineage = self._lineage if lineage is _MISSING else lineage
        if self._depth + 1 >= _FLATTEN_DEPTH:
            flat = dict(self._materialized())
            flat.update(updates)
            for key in removed:
                flat.pop(key, None)
            child._parent = None
            child._updates = flat
            child._removed = ()
            child._depth = 0
            child._cache = flat
            return child
        child._parent = self
        child._updates = updates
        child._removed = removed
        child._depth = self._depth + 1
        child._cache = None
        return child

    def _share(self, trace_id: Optional[str], lineage: List[str]) -> 'Payload[T]':
        """Same contents, different trace/lineage: shares the whole chain."""
        twin = Payload.__new__(Payload)
        twin._parent = self._parent
        twin._updates = self._updates
        twin._removed = self._removed
        twin._depth = self._depth
        twin._cache = self._cache
        twin._trace_id = trace_id
        twin._lineage = lineage
        return twin

    def _materialized(self) -> Dict[str, Any]:
        """The flat contents, cached. Read-only: callers must copy to change."""
        cache = self._cache
        if cache is None:
            cache = dict(self._parent._materialized())  # type: ignore[union-attr]
            cache.update(self._updates)
            for key in self._removed:
                cache.pop(key, None)
            self._cache = cache
        return cache

    @property
    def _data(self) -> Dict[str, Any]:
        """Flat contents (read-only; kept for code that inspected ``_data``)."""
        return self._materialized()

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for key, or default if absent."""
        node = self
        while True:
            value = node._updates.get(key, _MISSING)
            if value is not _MISSING:
                return value
            parent = node._parent
            if parent is None or (node._removed and key in node._removed):
                return default
            node = parent

    @property
    def trace_id(self) -> Optional[str]:
        """Trace ID for distributed tracing / lineage tracking."""
        return self._trace_id

    @property
    def lineage(self) -> List[str]:
        """Ordered list of step names this payload has passed through."""
        return list(self._lineage)

    def with_trace(self, trace_id: str) -> 'Payload[T]':
        """Return a new Payload with trace ID set."""
        return self._share(trace_id, self._lineage)

    def _stamp(self, step_name: str) -> 'Payload[T]':
        """Record a processing step in lineage (internal). Shares the contents."""
        return self._share(self._trace_id, self._lineage + [step_name])

    def has(self, key: str) -> bool:
        """Whether ``key`` is present (even with a ``None`` value)."""
        node = self
        while True:
            if key in node._updates:
                return True
            parent = node._parent
            if parent is None or (node._removed and key in node._removed):
                return False
            node = parent

    def remove(self, key: str) -> 'Payload[T]':
        """Return a new Payload without ``key`` (a no-op if it is absent)."""
        if not self.has(key):
            return self
        return self._child({}, (key,))

    def insert(self, key: str, value: Any) -> 'Payload[T]':
        """Return a fresh Payload with the addition."""
        return self._child({key: value}, ())

    def insert_as(self, key: str, value: Any) -> 'Payload[T]':
        """
        Create a new Payload with type evolution — allows clean transformation
        between TypedDict shapes without explicit casting.
        """
        return self._child({key: value}, ())

    def replace_data(self, data: Dict[str, Any]) -> 'Payload[T]':
        """Return a new Payload with `data` as its entire contents.

        Unlike `insert`, which adds one key, this swaps the whole dict — the
        shape a dict-style filter naturally produces (`doc = dict(...);
        ...mutate doc...; return doc`). Trace ID and lineage carry over,
        which `type(payload)(data)` does not: that reconstructs a bare
        Payload with neither, silently dropping both.
        """
        return Payload[T]._from_parts(dict(data), trace_id=self._trace_id, _lineage=self._lineage)

    def with_mutation(self) -> 'MutablePayload[T]':
        """Convert to a mutable sibling for performance-critical sections."""
        return MutablePayload[T]._from_parts(dict(self._materialized()), trace_id=self._trace_id,
                                             _lineage=self._lineage)

    def merge(self, other: 'Payload[T]') -> 'Payload[T]':
        """Combine payloads, with other taking precedence on conflicts."""
        trace = self._trace_id or getattr(other, '_trace_id', None)
        lineage = self._lineage + getattr(other, '_lineage', [])
        return self._child(other.to_dict(), (), trace_id=trace, lineage=lineage)

    def to_dict(self) -> Dict[str, Any]:
        """Express as dict for ecosystem integration."""
        return dict(self._materialized())

    def serialize(self, fmt: str = "json") -> bytes:
        """Serialize payload for network/storage transport.

        Supported formats:
          - "json"    — human-readable, universal (default)
          - "msgpack" — binary, ~2x faster (requires msgpack package)
          - "shm"     — shared memory handle (same-machine only)
        """
        envelope = {"data": self._materialized()}
        if self._trace_id:
            envelope["trace_id"] = self._trace_id
        if self._lineage:
            envelope["lineage"] = self._lineage

        if fmt == "json":
            return json.dumps(envelope).encode("utf-8")
        if fmt == "msgpack":
            try:
                import msgpack  # type: ignore[import-untyped]
            except ImportError:
                raise ImportError(
                    "msgpack is required for fmt='msgpack'. "
                    "Install it with: pip install msgpack"
                )
            return msgpack.packb(envelope, use_bin_type=True)
        if fmt == "shm":
            from .shared_payload import SharedPayload as _SP
            sp = _SP.from_payload(self)
            handle = sp.handle()
            return json.dumps(handle).encode("utf-8")
        raise ValueError(f"Unsupported format: {fmt}")

    @classmethod
    def deserialize(cls, raw: bytes, fmt: str = "json") -> 'Payload':
        """Deserialize payload from network/storage transport."""
        if fmt == "json":
            envelope = json.loads(raw.decode("utf-8"))
            data = envelope.get("data", {})
            if not isinstance(data, dict):
                data = dict(data)
            return cls._from_parts(
                data,
                trace_id=envelope.get("trace_id"),
                _lineage=envelope.get("lineage"),
            )
        if fmt == "msgpack":
            try:
                import msgpack  # type: ignore[import-untyped]
            except ImportError:
                raise ImportError(
                    "msgpack is required for fmt='msgpack'. "
                    "Install it with: pip install msgpack"
                )
            envelope = msgpack.unpackb(raw, raw=False)
            data = envelope.get("data", {})
            if not isinstance(data, dict):
                data = dict(data)
            return cls._from_parts(
                data,
                trace_id=envelope.get("trace_id"),
                _lineage=envelope.get("lineage"),
            )
        if fmt == "shm":
            from .shared_payload import SharedPayload as _SP
            handle = json.loads(raw.decode("utf-8"))
            sp = _SP.from_handle(handle)
            p = sp.to_payload()
            sp.close()
            return p
        raise ValueError(f"Unsupported format: {fmt}")

    def __repr__(self) -> str:
        if self._trace_id:
            return f"Payload({self._materialized()}, trace_id='{self._trace_id}')"
        return f"Payload({self._materialized()})"


class MutablePayload(Generic[T]):
    """
    Mutable data container for performance-critical sections.
    Enhanced with generic typing for type-safe workflows.
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None, *,
                 trace_id: Optional[str] = None, _lineage: Optional[List[str]] = None):
        self._data = data or {}
        self._trace_id = trace_id
        self._lineage = list(_lineage) if _lineage else []

    @classmethod
    def _from_parts(
        cls,
        data: Dict[str, Any],
        *,
        trace_id: Optional[str] = None,
        _lineage: Optional[List[str]] = None,
    ) -> 'MutablePayload[T]':
        """Construct a MutablePayload from owned data without cloning again."""
        payload = cls.__new__(cls)
        payload._data = data
        payload._trace_id = trace_id
        payload._lineage = list(_lineage) if _lineage else []
        return payload

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Change in place."""
        self._data[key] = value

    def remove(self, key: str) -> None:
        """Remove ``key`` in place (a no-op if it is absent)."""
        self._data.pop(key, None)

    def has(self, key: str) -> bool:
        return key in self._data

    @property
    def trace_id(self) -> Optional[str]:
        """Trace ID for distributed tracing / lineage tracking."""
        return self._trace_id

    @property
    def lineage(self) -> List[str]:
        """Ordered list of step names this payload has passed through."""
        return list(self._lineage)

    def to_immutable(self) -> Payload[T]:
        """Return to safety with a fresh immutable copy."""
        return Payload[T]._from_parts(self._data.copy(), trace_id=self._trace_id, _lineage=self._lineage)

    def __repr__(self) -> str:
        return f"MutablePayload({self._data})"
