"""Add: a Filter of the conformance vocabulary (conformance/README.md)."""


class Add:
    def __init__(self, key, by):
        self.key = key
        self.by = by

    def call(self, payload):
        return payload.insert(self.key, payload.get(self.key, 0) + self.by)
