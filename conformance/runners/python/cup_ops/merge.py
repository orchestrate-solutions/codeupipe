"""Merge: a Filter of the conformance vocabulary (conformance/README.md)."""

from codeupipe import Payload


class Merge:
    def __init__(self, value):
        self.value = value

    def call(self, payload):
        return payload.merge(Payload(self.value))
