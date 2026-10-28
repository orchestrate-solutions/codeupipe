"""AttachRecordHookFilter: the Hook that records the lifecycle, for a case that asks for it."""

import cup_ops as ops
from codeupipe import Payload


class AttachRecordHookFilter:
    """Filter (sync).

    Input keys: ``case``, ``pipeline``, ``compiled``, ``observe``.
    Output keys: ``hooks``: the Hooks of the run, or None. A case with
    ``"hooks"`` gets a RecordHook, on the pipeline too. Compiled code calls
    Hooks only when it was compiled with ``observe``.
    """

    def call(self, payload: Payload) -> Payload:
        wanted = payload.get("case").get("hooks") and (not payload.get("compiled") or payload.get("observe"))
        if not wanted:
            return payload.insert("hooks", None)
        hook = ops.RecordHook()
        payload.get("pipeline").use_hook(hook)
        return payload.insert("hooks", [hook])
