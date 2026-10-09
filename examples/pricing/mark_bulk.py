"""MarkBulk: a Filter."""


class MarkBulk:
    def call(self, payload):
        return payload.insert("bulk", True)
