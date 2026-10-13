"""NoTargetsNamedPredicate: did the caller name no target?"""

from codeupipe import Payload


class NoTargetsNamedPredicate:
    """True when ``names`` is empty: the judge then takes each target that this machine can run."""

    def test(self, payload: Payload) -> bool:
        return not payload.get("names")
