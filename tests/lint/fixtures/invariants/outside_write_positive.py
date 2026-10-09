"""CUP-I004: a Tap, a Hook or a predicate that writes to the Payload."""

from codeupipe import Hook, Payload


class TapInserts:
    def observe(self, payload):
        payload.insert("seen", True)  # expect: CUP-I004


class TapRemoves:
    def observe(self, payload):
        payload.remove("secret")  # expect: CUP-I004


class TapMerges:
    def observe(self, payload):
        payload.merge(Payload({"seen": True}))  # expect: CUP-I004


class TapSetsTheTrace:
    def observe(self, payload):
        payload.with_trace("t")  # expect: CUP-I004


class TapChains:
    def observe(self, payload):
        payload.insert("a", 1).insert("b", 2)  # expect: CUP-I004


class TapNamesItDifferently:
    def observe(self, p):
        p.insert("seen", True)  # expect: CUP-I004


class AsyncTapInserts:
    async def observe(self, payload):
        payload.insert("seen", True)  # expect: CUP-I004


class PredicateInserts:
    def test(self, payload):
        payload.insert("checked", True)  # expect: CUP-I004
        return True


class HookWrites(Hook):
    def before(self, step, payload):
        payload.insert("started", step)  # expect: CUP-I004

    def after(self, step, payload):
        payload.remove("started")  # expect: CUP-I004

    def on_error(self, step, error, payload):
        payload.insert("error", str(error))  # expect: CUP-I004
