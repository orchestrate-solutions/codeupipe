"""Predicate: a Valve's condition (conformance/API.md, "Valve").

An object with ``test(payload) -> bool``, identified by its class like a
step, with any configuration on the instance::

    class AtLeast:
        def __init__(self, n):
            self.n = n

        def test(self, payload):
            return payload.get("n", 0) >= self.n

Functions, lambdas and closures are not predicates.
"""

from typing import Any, Protocol

__all__ = ["Predicate"]


class Predicate(Protocol):
    def test(self, payload: Any) -> bool:
        ...
