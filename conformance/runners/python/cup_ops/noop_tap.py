"""NoopTap: a Tap of the conformance vocabulary (conformance/README.md)."""


class NoopTap:
    """Benchmarks: a Tap that does nothing, so Plane B cost is the handoff."""

    def observe(self, payload):
        pass
