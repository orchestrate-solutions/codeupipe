"""A Hook that records every lifecycle event with a deep snapshot of the
payload it was handed, and keeps the reference it was handed.

Used for two checks at once:

* hook parity: the (event, step, snapshot) sequence of the dynamic run and
  of the observable export must be identical;
* isolation: at the end of the run, every held reference must still equal
  its snapshot. If it does not, some later step wrote into a payload an
  earlier step had already produced.

It works on both sides: the dynamic run hands it a ``Payload``, the
observable export a ``dict``.
"""

import copy

from scorecard.strict import strict_equal

__all__ = ["SnapshotHook"]


def _as_dict(payload):
    to_dict = getattr(payload, "to_dict", None)
    return to_dict() if callable(to_dict) else payload


class SnapshotHook:
    def __init__(self):
        self.events = []  # (event, step, snapshot, error or None)
        self.refs = []    # (index into events, the object as handed over)

    def _record(self, event, step, payload, error=None):
        self.refs.append((len(self.events), payload))
        err = None if error is None else f"{type(error).__name__}: {error}"
        self.events.append((event, step, copy.deepcopy(_as_dict(payload)), err))

    def before(self, step, payload):
        self._record("before", step, payload)

    def after(self, step, payload):
        self._record("after", step, payload)

    def on_error(self, step, error, payload):
        self._record("error", step, payload, error)

    def sequence(self):
        """[(event, step, snapshot, error)] for parity comparison."""
        return list(self.events)

    def mutated_after_the_fact(self):
        """Events whose payload changed after the hook saw it: [(i, event, step)]."""
        changed = []
        for index, ref in self.refs:
            event, step, snapshot, _ = self.events[index]
            if not strict_equal(_as_dict(ref), snapshot):
                changed.append((index, event, step))
        return changed
