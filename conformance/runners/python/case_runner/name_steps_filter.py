"""NameStepsFilter: give each step in the result the name that the case gives it."""

from codeupipe import Payload


class NameStepsFilter:
    """Filter (sync).

    Input keys: ``result``, ``label`` ({step label: name in the case}).
    Output keys: ``result``, with the name of the case for each step in
    ``state``, ``pipeline_state``, ``inner_states`` and ``hooks``. A label
    that is not in ``label`` stays as it is.
    """

    def call(self, payload: Payload) -> Payload:
        label = payload.get("label")
        named = {key: self.named(key, value, label) for key, value in payload.get("result").items()}
        return payload.insert("result", named)

    def named(self, key, value, label):
        """The value of one key of the result, with the names of the case where it has steps."""
        if key in ("state", "pipeline_state"):
            return self.state(value, label)
        if key == "inner_states":
            return [self.state(one, label) for one in value]
        if key == "hooks":
            return [self.event(event, label) for event in value]
        return value

    def state(self, state, label) -> dict:
        return {key: [label.get(step, step) for step in steps] for key, steps in state.items()}

    def event(self, event, label) -> str:
        phase, _, step = event.partition(":")
        return f"{phase}:{label.get(step, step)}"
