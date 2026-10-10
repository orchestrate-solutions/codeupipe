"""RecordHook: a Hook of the conformance vocabulary (conformance/README.md)."""

from conformance_sink import HOOKS


class RecordHook:
    """Records ``before:<step>``, ``after:<step>``, ``error:<step>``; the
    pipeline-level events use an empty step. Hooks receive step labels;
    the runner maps them back to the case's step names (runner.labels)."""

    def before(self, step, payload):
        HOOKS.append("before:" + (step or ""))

    def after(self, step, payload):
        HOOKS.append("after:" + (step or ""))

    def on_error(self, step, error, payload):
        HOOKS.append("error:" + (step or ""))
