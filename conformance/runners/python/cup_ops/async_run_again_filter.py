"""AsyncRunAgainFilter: the reference `run_again` step for ``run_async`` (conformance/README.md)."""

from conformance_sink import RUN_AGAIN


class AsyncRunAgainFilter:
    """``RunAgainFilter`` for a pipeline that runs with ``run_async``."""

    def __init__(self, data):
        self.data = data

    async def call(self, payload):
        if payload.get("inner") is not True:
            await RUN_AGAIN[0](dict(self.data))
        return payload
