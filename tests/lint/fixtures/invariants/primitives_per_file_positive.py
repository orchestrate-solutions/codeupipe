"""CUP-I005: more than one primitive in a file."""

from codeupipe import Hook, Pipeline


class First:
    def call(self, payload):
        return payload


class SecondFilter:  # expect: CUP-I005
    def call(self, payload):
        return payload


class ATap:  # expect: CUP-I005
    def observe(self, payload):
        pass


class AnAsyncTap:  # expect: CUP-I005
    async def observe(self, payload):
        pass


class APredicate:  # expect: CUP-I005
    def test(self, payload):
        return True


class AHook(Hook):  # expect: CUP-I005
    def before(self, step, payload):
        pass


class AHookByShape:  # expect: CUP-I005
    def before(self, step, payload):
        pass

    def after(self, step, payload):
        pass

    def on_error(self, step, error, payload):
        pass


class APipeline(Pipeline):  # expect: CUP-I005
    def __init__(self):
        super().__init__()
        self.add_filter(First())
