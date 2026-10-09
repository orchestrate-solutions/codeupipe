"""Not CUP-I005: one primitive, with the plain classes and functions it needs."""

from dataclasses import dataclass


@dataclass
class Settings:
    rate: float


class NotAStep:
    """``call`` with two arguments is not a Filter's call."""

    def call(self, payload, extra):
        return payload


class AlsoNotAStep:
    def test(self):
        return True

    def observe(self):
        pass


def helper(payload):
    class Local:  # a class inside a function is not a module's primitive
        def call(self, payload):
            return payload
    return Local


class TheOnlyFilter:
    def __init__(self, settings):
        self.settings = settings

    def call(self, payload):
        return payload.insert("rate", self.settings.rate)
