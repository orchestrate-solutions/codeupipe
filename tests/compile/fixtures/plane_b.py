"""Fixture: a Tap whose sink fails, for Plane B isolation in static mode."""


class Score:
    def call(self, payload):
        return payload.insert("score", 2)


class ExplodingTap:
    def observe(self, payload):
        raise ConnectionError("audit sink disconnected")


class Interrupting:
    def observe(self, payload):
        raise KeyboardInterrupt
