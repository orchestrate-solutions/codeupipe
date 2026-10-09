"""Nothing here is flagged."""

from codeupipe.core import State


class HasItsOwnAttributeCalledState:
    """``state`` here is the filter's own dict, not pipeline State."""

    def __init__(self):
        self.state = {}
        self.status = "ready"

    def call(self, payload):
        self.state["last"] = payload.get("id")
        return payload.insert("previous", self.state.get("last"))


class ReadsAPayloadKeyCalledState:
    def call(self, payload):
        if payload.get("state") == "active":
            return payload.insert("active", True)
        return payload


class ReadsANestedValueCalledState:
    def call(self, payload):
        order = payload.get("order", {})
        return payload.insert("shipped", order.get("state") == "shipped")


class TapMayObserveState:
    """A Tap is an observer; reading State from one is fine."""

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def observe(self, payload):
        print(len(self.pipeline.state.executed))


class HookMayObserveState:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def after(self, step, payload):
        print(self.pipeline.state.timings)


class UsesStateOutsideAStepMethod:
    def __init__(self, state: State):
        self.run_state = state

    def summary(self):
        return list(self.run_state.executed)

    def call(self, payload):
        return payload


def report(pipeline):
    """Code that runs a pipeline reads its State afterwards."""
    return pipeline.state.executed


class Suppressed:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def call(self, payload):
        return payload.insert("n", len(self.pipeline.state.executed))  # cup: allow-state-read
