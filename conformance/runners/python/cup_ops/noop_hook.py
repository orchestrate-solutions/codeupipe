"""NoopHook: a Hook of the conformance vocabulary (conformance/README.md)."""


class NoopHook:
    def before(self, step, payload):
        pass

    def after(self, step, payload):
        pass

    def on_error(self, step, error, payload):
        pass
