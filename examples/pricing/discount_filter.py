"""DiscountFilter: a Filter."""


class DiscountFilter:
    """Takes the Payload, writes to it, returns it."""

    def __init__(self, rate):
        self.rate = rate

    def call(self, payload):
        return payload.insert("price", round(payload.get("price", 0) * (1 - self.rate), 2))
