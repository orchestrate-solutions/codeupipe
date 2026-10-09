"""AtLeastPredicate: a predicate, the question a Valve asks."""


class AtLeastPredicate:
    """An object with test(payload). Its settings are on the instance, so the
    same class answers a different question in another pipeline."""

    def __init__(self, key, minimum):
        self.key = key
        self.minimum = minimum

    def test(self, payload):
        return payload.get(self.key, 0) >= self.minimum
