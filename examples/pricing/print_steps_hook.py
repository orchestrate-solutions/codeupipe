"""PrintStepsHook: a Hook."""

from codeupipe import Hook


class PrintStepsHook(Hook):
    """Sees the lifecycle. ``step`` is the label of the step, which is the
    name of its class. It is None for the pipeline itself."""

    def before(self, step, payload):
        if step is not None:
            print("  " + step)

    def after(self, step, payload):
        pass

    def on_error(self, step, error, payload):
        pass
