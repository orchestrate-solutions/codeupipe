"""MutateFilter: a Filter of the conformance vocabulary (conformance/README.md)."""


class MutateFilter:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def call(self, payload):
        payload.insert(self.key, self.value)
        return payload
