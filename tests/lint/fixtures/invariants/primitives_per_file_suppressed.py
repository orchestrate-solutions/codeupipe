"""CUP-I005, suppressed on purpose."""


class First:
    def call(self, payload):
        return payload


class Second:  # cup: allow-shared-file
    def call(self, payload):
        return payload
