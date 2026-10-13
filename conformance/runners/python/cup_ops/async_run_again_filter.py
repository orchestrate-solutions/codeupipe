"""AsyncRunAgainFilter: the reference `run_again` step for ``run_async`` (conformance/README.md)."""

from codeupipe import Payload, State

from conformance_sink import INNER_STATES


class AsyncRunAgainFilter:
    """``RunAgainFilter`` for a pipeline that runs with ``run_async``."""

    def __init__(self, data):
        self.data = data
        self.pipeline = None

    async def call(self, payload):
        if payload.get("inner") is not True:
            state = State()
            INNER_STATES.append(state)
            await self.pipeline.run_async(Payload(dict(self.data)), state)
        return payload
