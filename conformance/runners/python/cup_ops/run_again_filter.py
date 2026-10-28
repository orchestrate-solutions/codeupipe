"""RunAgainFilter: the reference `run_again` step (conformance/README.md)."""

from conformance_sink import RUN_AGAIN


class RunAgainFilter:
    """Starts a second run of the pipeline that it is in, inside the first one.

    How a pipeline is run again depends on the target, so the runner gives
    that as a function, in ``RUN_AGAIN``. The second run has ``inner`` in its
    input, so it does not start a third one.
    """

    def __init__(self, data):
        self.data = data

    def call(self, payload):
        if payload.get("inner") is not True:
            RUN_AGAIN[0](dict(self.data))
        return payload
