"""ParseTargetFilter: what the name of a target means."""

from codeupipe import Payload

_DYNAMIC = {"compiled": False, "run_async": False, "lowering": "", "observe": False}
_TARGETS = {
    "run": _DYNAMIC,
    "run_async": {**_DYNAMIC, "run_async": True},
    "static-steps": {"compiled": True, "run_async": False, "lowering": "steps", "observe": False},
    "static-inline": {"compiled": True, "run_async": False, "lowering": "inline", "observe": False},
    "static-observe": {"compiled": True, "run_async": False, "lowering": "steps", "observe": True},
}


class ParseTargetFilter:
    """Filter (sync).

    Input keys: ``target`` (``run``, ``run_async``, ``static-steps``,
    ``static-inline`` or ``static-observe``).
    Output keys: ``compiled`` (the case runs as compiled code), ``run_async``,
    ``lowering`` (the layout of the compiled code) and ``observe`` (the
    compiled code records State and calls Hooks).

    ``allowed`` is the targets that this run takes, and ``what`` is the word
    for them in the message for another name.
    """

    def __init__(self, allowed=tuple(_TARGETS), what="target"):
        self.allowed = allowed
        self.what = what

    def call(self, payload: Payload) -> Payload:
        target = payload.get("target")
        if target not in self.allowed:
            raise SystemExit(f"unknown {self.what} {target!r}")
        return payload.merge(Payload(dict(_TARGETS[target])))
