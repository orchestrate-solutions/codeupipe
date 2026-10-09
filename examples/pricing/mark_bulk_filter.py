"""MarkBulkFilter: a Filter."""


class MarkBulkFilter:
    def call(self, payload):
        return payload.insert("bulk", True)
