"""Reference steps for the conformance vocabulary (conformance/README.md).

Ordinary CUP components configured through their constructors, so the
static targets exercise constructor-config baking as well as lowering.
"""

from conformance_sink import HOOKS, TAPS
from codeupipe import Payload, Pipeline


class Set:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def call(self, payload):
        return payload.insert(self.key, self.value)


class Copy:
    def __init__(self, source, target):
        self.source = source
        self.target = target

    def call(self, payload):
        return payload.insert(self.target, payload.get(self.source))


class Add:
    def __init__(self, key, by):
        self.key = key
        self.by = by

    def call(self, payload):
        return payload.insert(self.key, payload.get(self.key, 0) + self.by)


class Append:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def call(self, payload):
        return payload.insert(self.key, list(payload.get(self.key) or []) + [self.value])


class Remove:
    def __init__(self, key):
        self.key = key

    def call(self, payload):
        return payload.remove(self.key)


class Merge:
    def __init__(self, value):
        self.value = value

    def call(self, payload):
        return payload.merge(Payload(self.value))


class Has:
    def __init__(self, key, target):
        self.key = key
        self.target = target

    def call(self, payload):
        return payload.insert(self.target, payload.has(self.key))


class Mutate:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def call(self, payload):
        mutable = payload.with_mutation()
        mutable.set(self.key, self.value)
        return mutable.to_immutable()


class Fail:
    def __init__(self, message):
        self.message = message

    def call(self, payload):
        raise RuntimeError(self.message)


class RecordTap:
    def __init__(self, key):
        self.key = key

    def observe(self, payload):
        TAPS.append(payload.get(self.key))


class NoopTap:
    """Benchmarks: a Tap that does nothing, so Plane B cost is the handoff."""

    def observe(self, payload):
        pass


class NoopHook:
    def before(self, step, payload):
        pass

    def after(self, step, payload):
        pass

    def on_error(self, step, error, payload):
        pass


class FailTap:
    def __init__(self, message):
        self.message = message

    def observe(self, payload):
        raise RuntimeError(self.message)


class Nested(Pipeline):
    """The runner's named pipeline type: nested pipelines must be named
    types (conformance/API.md, step identity)."""


class RecordHook:
    """Records ``before:<step>``, ``after:<step>``, ``error:<step>``; the
    pipeline-level events use an empty step. Hooks receive step identities;
    the runner maps them back to the case's step names (runner.labels)."""

    def before(self, step, payload):
        HOOKS.append("before:" + (step or ""))

    def after(self, step, payload):
        HOOKS.append("after:" + (step or ""))

    def on_error(self, step, error, payload):
        HOOKS.append("error:" + (step or ""))
