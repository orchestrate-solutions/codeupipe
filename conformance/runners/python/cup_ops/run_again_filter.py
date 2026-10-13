"""RunAgainFilter: the reference `run_again` step (conformance/README.md)."""

from codeupipe import Payload, State

from conformance_sink import INNER_STATES


class RunAgainFilter:
    """Starts a second run of the pipeline that it is in, inside the first one.

    The runner sets ``pipeline`` after it builds the pipeline. The second run
    has ``inner`` in its input, so it does not start a third one.
    """

    def __init__(self, data):
        self.data = data
        self.pipeline = None

    def call(self, payload):
        if payload.get("inner") is not True:
            state = State()
            INNER_STATES.append(state)
            self.pipeline.run(Payload(dict(self.data)), state)
        return payload
