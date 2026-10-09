"""Fixture: filters that lean on their own module's top-level names.

Real filters are written this way — a rate constant, a compiled regex, a
small helper — and export used to drop every one of these names silently.
"""

import re as _re
from math import pi

_BASE = 3
_LIMIT = _BASE * 2
_RATE = 0.5
_WORDS = _re.compile(r"[a-z]+")
_SEEN = []


def _double(x):
    return x * 2


class UsesConstant:
    def call(self, payload):
        return payload.insert("price", payload.get("price", 0) * _RATE)


class UsesTransitiveConstant:
    def call(self, payload):
        return payload.insert("limit", _LIMIT)


class UsesHelper:
    def call(self, payload):
        return payload.insert("doubled", _double(payload.get("x", 0)))


class UsesCompiledRegex:
    def call(self, payload):
        return payload.insert("words", _WORDS.findall(payload.get("text", "")))


class UsesFromImportConstant:
    def call(self, payload):
        return payload.insert("tau", 2 * pi)


class RecordsToModuleList:
    def observe(self, payload):
        _SEEN.append(payload.get("x"))


globals()["_INJECTED"] = 5


class UsesInjected:
    def call(self, payload):
        return payload.insert("n", _INJECTED)  # noqa: F821 — injected above
