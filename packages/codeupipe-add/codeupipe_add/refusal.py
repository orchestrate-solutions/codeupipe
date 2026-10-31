"""Refusal: the command cannot do what it was asked, and writes nothing."""


class Refusal(Exception):
    """``exit_code`` is 1 when a file exists, and 2 when the arguments are wrong
    (conformance/ADD.md)."""

    def __init__(self, exit_code, message):
        super().__init__(message)
        self.exit_code = exit_code
