"""Not CUP-I004: a Filter writes; a Tap, a Hook or a predicate reads, or writes its own copy."""

from codeupipe import Hook


class FilterWrites:
    def call(self, payload):
        payload.insert("a", 1)
        return payload.remove("b")


class TapReads:
    def __init__(self):
        self.seen = []

    def observe(self, payload):
        self.seen.append(payload.get("a"))
        self.seen.insert(0, payload.has("b"))


class TapWritesItsOwnCopy:
    def observe(self, payload):
        mine = payload.copy()
        mine.insert("note", "mine")
        payload.copy().insert("also", "mine")


class PredicateReads:
    def test(self, payload):
        return payload.get("qty", 0) >= 10


class HookReads(Hook):
    def __init__(self):
        self.rows = []

    def before(self, step, payload):
        self.rows.insert(0, (step, payload.to_dict()))

    def after(self, step, payload):
        pass

    def on_error(self, step, error, payload):
        self.rows.append((step, error))


class NotAStepMethod:
    def helper(self, payload):
        payload.insert("a", 1)


class WritesOnPurpose:
    def observe(self, payload):
        payload.insert("seen", True)  # cup: allow-outside-write
