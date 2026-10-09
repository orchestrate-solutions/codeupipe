"""PrintSteps: a Hook."""

from codeupipe import Hook


class PrintSteps(Hook):
    """Sees the lifecycle. ``step`` is the step's identity; it is None for
    the pipeline itself."""

    def before(self, step, payload):
        if step is not None:
            print("  " + step.replace("examples.pricing.", ""))

    def after(self, step, payload):
        pass

    def on_error(self, step, error, payload):
        pass
