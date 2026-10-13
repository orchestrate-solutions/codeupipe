"""FinishResultFilter: the id of the case and what its Taps recorded."""

import conformance_sink as sink
from codeupipe import Payload


class FinishResultFilter:
    """Filter (sync).

    Input keys: ``case``, ``result``.
    Output keys: ``result``, with ``id`` and ``taps``.
    """

    def call(self, payload: Payload) -> Payload:
        result = {**payload.get("result"), "id": payload.get("case")["id"], "taps": list(sink.TAPS)}
        return payload.insert("result", result)
