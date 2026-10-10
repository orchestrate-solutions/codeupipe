"""Step probe cases, with describe(label, f) replaced by
p.add_filter(f): the probe's cases as lint fixtures."""

from codeupipe import Pipeline

from app.filters import Validate, normalize


def make_closure(k):
    def inner(payload):
        return {**payload, k: 1}
    return inner


def make_local_class():
    class Local:
        def call(self, payload):
            return payload
    return Local()


class DefinedInEntryScript:
    def call(self, payload):
        return payload


p = Pipeline()
p.add_filter(Validate())
p.add_filter(Validate())
p.add_filter(normalize)
p.add_filter(lambda payload: payload)  # expect: CUP-A001
p.add_filter(make_closure("x"))  # expect: CUP-A002
p.add_filter(make_local_class())  # expect: CUP-A003
p.add_filter(DefinedInEntryScript())  # not flagged: a module-level class
