"""Fixture: filters configured through their constructor — the CUP idiom
("inject via constructor config"), which export used to lower into a
function body that referenced an undefined ``self``."""


class Discount:
    def __init__(self, rate):
        self.rate = rate

    def call(self, payload):
        return payload.insert("price", round(payload.get("price", 0) * (1 - self.rate), 2))


class KeepKeys:
    def __init__(self, keys, label=None):
        self.keys = keys
        self.label = label

    def call(self, payload):
        for key in payload.to_dict():
            if key not in self.keys:
                payload = payload.remove(key)
        return payload.insert("label", self.label)


class Tagger:
    def __init__(self, tags):
        self.tags = tags

    def observe(self, payload):
        self.tags.get("seen")


class HoldsAnObject:
    def __init__(self):
        self.client = object()

    def call(self, payload):
        return payload.insert("client", repr(self.client))


class CountsCalls:
    def __init__(self):
        self.count = 0

    def call(self, payload):
        self.count = self.count + 1
        return payload.insert("count", self.count)


class UsesAHelperMethod:
    def _double(self, x):
        return x * 2

    def call(self, payload):
        return payload.insert("x", self._double(payload.get("x", 0)))


class SetFlag:
    """Configured through ``self.key``, like the predicate beside it."""

    def __init__(self, key):
        self.key = key

    def call(self, payload):
        return payload.insert(self.key, True)


class AtLeast:
    """A configurable predicate object (conformance/API.md, "Valve")."""

    def __init__(self, key, n):
        self.key = key
        self.n = n

    def test(self, payload):
        return payload.get(self.key, 0) >= self.n
