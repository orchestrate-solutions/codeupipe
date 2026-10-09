"""
State: what happened in the last run.

Which steps executed, which a Valve skipped, the errors, and the timings
when timing is on. Read it after a run through ``pipeline.state``.
"""

from typing import Dict, List, Tuple

__all__ = ["State"]


class State:
    """The record of one run. A run starts with a new State.

    - ``executed``: step identities, in order
    - ``skipped``: steps a Valve did not run
    - ``errors``: (identity, error) pairs
    - ``timings``: identity -> seconds, when timing is on
    """

    def __init__(self):
        self.executed: List[str] = []
        self.skipped: List[str] = []
        self.errors: List[Tuple[str, Exception]] = []
        self.timings: Dict[str, float] = {}

    def mark_executed(self, name: str) -> None:
        """Record that a step executed."""
        self.executed.append(name)

    def mark_skipped(self, name: str) -> None:
        """Record that a step was skipped."""
        self.skipped.append(name)

    def record_timing(self, name: str, duration: float) -> None:
        """Record a step's duration in seconds."""
        self.timings[name] = duration

    def record_error(self, name: str, error: Exception) -> None:
        """Record an error against a step."""
        self.errors.append((name, error))

    def __repr__(self) -> str:
        return (
            f"State(executed={self.executed}, skipped={self.skipped}, "
            f"errors={len(self.errors)}, timings={len(self.timings)})"
        )
