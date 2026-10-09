"""RemoveFilter: a Filter of the conformance vocabulary (conformance/README.md)."""


class RemoveFilter:
    def __init__(self, key):
        self.key = key

    def call(self, payload):
        return payload.remove(self.key)
