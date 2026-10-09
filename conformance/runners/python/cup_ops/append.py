"""Append: a Filter of the conformance vocabulary (conformance/README.md)."""


class Append:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def call(self, payload):
        return payload.insert(self.key, list(payload.get(self.key) or []) + [self.value])
