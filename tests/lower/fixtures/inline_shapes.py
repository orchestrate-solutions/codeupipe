"""Fixture: step shapes that make inlining + in-place writes risky.

Each one is a way a flattened ``run()`` that mutates one private dict could
diverge from the dynamic runtime.
"""

KEPT = []
SEEN_BY_TAP = []


class SetA:
    def call(self, payload):
        return payload.insert("a", 1)


class ChainReadsItsOwnWrite:
    """A write changes the Payload at once, so the second link reads the
    ``a`` that the first link wrote."""

    def call(self, payload):
        return payload.insert("a", 100).insert("b", payload.get("a"))


class EarlyReturn:
    def call(self, payload):
        if payload.get("a"):
            return payload.insert("early", True)
        return payload


class KeepsACopy:
    """A step that keeps the payload keeps a copy: later writes do not
    reach it."""

    def call(self, payload):
        KEPT.append(payload.to_dict())
        KEPT.append(payload.copy().to_dict())
        return payload.insert("kept", True)


class TapKeepsACopy:
    def observe(self, payload):
        SEEN_BY_TAP.append(payload.to_dict())


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
