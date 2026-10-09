"""Has: a Filter of the conformance vocabulary (conformance/README.md)."""


class Has:
    def __init__(self, key, target):
        self.key = key
        self.target = target

    def call(self, payload):
        return payload.insert(self.target, payload.has(self.key))
