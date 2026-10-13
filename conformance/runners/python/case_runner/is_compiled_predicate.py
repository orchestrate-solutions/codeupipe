"""IsCompiledPredicate: does the case run as compiled code?"""

from codeupipe import Payload


class IsCompiledPredicate:
    """True when ``compiled`` is the value that was given (True unless said)."""

    def __init__(self, compiled=True):
        self.compiled = compiled

    def test(self, payload: Payload) -> bool:
        return payload.get("compiled") is self.compiled
