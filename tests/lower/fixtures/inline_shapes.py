"""Fixture: step shapes that make inlining + in-place writes risky.

Each one is a way a flattened ``run()`` that mutates one private dict could
diverge from the dynamic runtime, where every Payload is immutable.
"""

KEPT = []
SEEN_BY_TAP = []


class SetA:
    def call(self, payload):
        return payload.insert("a", 1)


class ChainReadsOldValue:
    """Immutable semantics: ``payload.get("a")`` sees the payload *before*
    this chain, so ``b`` must be the old ``a`` even though ``a`` is also
    being written in the same chain."""

    def call(self, payload):
        return payload.insert("a", 100).insert("b", payload.get("a"))


class EarlyReturn:
    def call(self, payload):
        if payload.get("a"):
            return payload.insert("early", True)
        return payload


class KeepsReference:
    """Stores the payload itself. A later in-place write must not show up
    in what was stored."""

    def call(self, payload):
        KEPT.append(payload.to_dict())
        KEPT.append(payload)
        return payload.insert("kept", True)


class TapKeepsReference:
    def observe(self, payload):
        SEEN_BY_TAP.append(payload)


class TapReadsOnly:
    def observe(self, payload):
        SEEN_BY_TAP.append(payload.get("a"))


class AIsSet:

    def test(self, payload):
        return payload.get('a') == 1


# --- dict-style steps: the shape generated code uses ------------------------


def flag_on(d):
    return d.get("on") is True


class ViaHelper:

    def test(self, payload):
        return flag_on(payload.to_dict())


class HasAndRemove:
    """Contract vocabulary that reads data without letting it escape."""

    def call(self, payload):
        return payload.remove("drop").insert("had_a", payload.has("a"))
