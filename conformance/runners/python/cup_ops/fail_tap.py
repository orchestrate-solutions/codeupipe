"""FailTap: a Tap of the conformance vocabulary (conformance/README.md)."""


class FailTap:
    def __init__(self, message):
        self.message = message

    def observe(self, payload):
        raise RuntimeError(self.message)
