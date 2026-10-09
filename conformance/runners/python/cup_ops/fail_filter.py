"""FailFilter: a Filter of the conformance vocabulary (conformance/README.md)."""


class FailFilter:
    def __init__(self, message):
        self.message = message

    def call(self, payload):
        raise RuntimeError(self.message)
