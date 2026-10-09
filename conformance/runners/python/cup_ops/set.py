"""Set: a Filter of the conformance vocabulary (conformance/README.md)."""


class Set:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def call(self, payload):
        return payload.insert(self.key, self.value)
