"""DropDisabledFilter: remove the findings of rules that are switched off."""

from codeupipe import Payload


class DropDisabledFilter:
    """Filter (sync).

    Input keys: ``findings``, optional ``suppressed``, optional ``disable`` (rule ids).
    Output keys: ``findings`` and ``suppressed`` without the findings of a
    disabled rule. A disabled rule is not counted as suppressed: it was not
    asked for.
    """

    def call(self, payload: Payload) -> Payload:
        disabled = set(payload.get("disable") or ())
        if not disabled:
            return payload
        payload.insert("findings", [f for f in payload.get("findings", []) if f.rule not in disabled])
        if payload.has("suppressed"):
            payload.insert("suppressed", [f for f in payload.get("suppressed", []) if f.rule not in disabled])
        return payload
