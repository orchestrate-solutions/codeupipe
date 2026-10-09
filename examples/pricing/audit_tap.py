"""AuditTap: a Tap."""


class AuditTap:
    """Reads the Payload and returns nothing. This one fails every time, to
    show that a Tap failure is recorded and never halts the run."""

    def observe(self, payload):
        raise ConnectionError("audit sink is down")
