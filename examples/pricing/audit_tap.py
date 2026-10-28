"""AuditTap: a Tap."""


class AuditTap:
    """Reads the Payload and returns nothing. If it fails, State records the
    error and the run goes on."""

    def observe(self, payload):
        print("audit:", payload.to_dict())
