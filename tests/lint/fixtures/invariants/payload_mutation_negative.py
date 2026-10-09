"""Nothing here is flagged."""


class CopiesFirst:
    def call(self, payload):
        items = list(payload.get("items", []))
        items.append(1)
        config = dict(payload.get("config", {}))
        config["debug"] = True
        tail = payload.get("items")[:]
        tail.append(2)
        twin = payload.get("config").copy()
        twin["x"] = 1
        ordered = sorted(payload.get("items", []))
        ordered.append(3)
        return payload.insert("items", items).insert("config", config)


class UsesTheSanctionedMutablePath:
    """In-place writes done on purpose, through the API."""

    def call(self, payload):
        scratch = payload.with_mutation()
        scratch.set("a", 1)
        scratch.remove("b")
        return scratch.to_immutable()


class UsesThePayloadApi:
    def call(self, payload):
        return payload.insert("a", 1).remove("b").merge(payload)


class RebindsScalars:
    def call(self, payload):
        count = payload.get("count", 0)
        count += 1
        name = payload.get("name", "")
        name = name.strip()
        return payload.insert("count", count).insert("name", name)


class RebindsBeforeMutating:
    def call(self, payload):
        items = payload.get("items", [])
        items = items + [1]
        items.append(2)
        return payload.insert("items", items)


class ReadsOnly:
    def call(self, payload):
        total = sum(payload.get("items", []))
        first = payload.get("items", [None])[0]
        keys = payload.get("config", {}).get("keys")
        return payload.insert("total", total).insert("first", first).insert("keys", keys)


class ChangesATopLevelCopy:
    def call(self, payload):
        data = payload.to_dict()
        data["a"] = 1
        return payload.replace_data(data)


class MutatesItsOwnState:
    def __init__(self):
        self.seen = []
        self._data = {}

    def observe(self, payload):
        self.seen.append(payload.get("id"))
        self._data["last"] = payload.get("id")


class MutatesUnrelatedLocals:
    def call(self, payload):
        out = []
        out.append(payload.get("a"))
        lookup = {}
        lookup["a"] = 1
        return payload.insert("out", out)


def helper_outside_a_step(payload):
    """Only step methods are checked: call, observe, test."""
    payload.get("items").append(1)


class Suppressed:
    def call(self, payload):
        payload.get("counter").append(1)  # cup: allow-mutation shared on purpose
        # cup: allow-mutation
        payload.get("counter").append(2)
        return payload
