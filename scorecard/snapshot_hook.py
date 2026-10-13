"""A Hook that records every lifecycle event with a deep snapshot of the
payload as it was at that event.

Used for hook parity: the (event, step, snapshot) sequence of the dynamic
run and of the observable export must be identical. A Payload is written in
place, so the snapshot is taken at the event; the object itself changes
later by design.

It works on both sides: the dynamic run hands it a ``Payload``, the
observable export a ``dict``.
"""

import copy

__all__ = ["SnapshotHook"]


class SnapshotHook:
    def __init__(self):
        self.events = []  # (event, step, snapshot, error or None)

    def _record(self, event, step, payload, error=None):
        err = None if error is None else f"{type(error).__name__}: {error}"
        self.events.append((event, step, copy.deepcopy(SnapshotHook._as_dict(payload)), err))

    def before(self, step, payload):
        self._record("before", step, payload)

    def after(self, step, payload):
        self._record("after", step, payload)

    def on_error(self, step, error, payload):
        self._record("error", step, payload, error)

    def sequence(self):
        """[(event, step, snapshot, error)] for parity comparison."""
        return list(self.events)

    @staticmethod
    def _as_dict(payload):
        to_dict = getattr(payload, "to_dict", None)
        return to_dict() if callable(to_dict) else payload
