"""RecordTap: a Tap of the conformance vocabulary (conformance/README.md)."""

from conformance_sink import TAPS


class RecordTap:
    def __init__(self, key):
        self.key = key

    def observe(self, payload):
        TAPS.append(payload.get(self.key))
