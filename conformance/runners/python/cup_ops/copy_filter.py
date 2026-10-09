"""CopyFilter: a Filter of the conformance vocabulary (conformance/README.md)."""


class CopyFilter:
    def __init__(self, source, target):
        self.source = source
        self.target = target

    def call(self, payload):
        return payload.insert(self.target, payload.get(self.source))
