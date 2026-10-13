"""AttachNoopHookFilter: a Hook that does nothing, for a scenario that measures the cost of Hooks."""

import cup_ops as ops
from codeupipe import Payload


class AttachNoopHookFilter:
    """Filter (sync).

    Input keys: ``case`` (a scenario), ``pipeline``.
    Output keys: ``hooks``: a list with one NoopHook for a scenario with
    ``"hooks": "noop"``, or None. The pipeline gets its own NoopHook.
    """

    def call(self, payload: Payload) -> Payload:
        if payload.get("case").get("hooks") != "noop":
            return payload.insert("hooks", None)
        payload.get("pipeline").use_hook(ops.NoopHook())
        return payload.insert("hooks", [ops.NoopHook()])
