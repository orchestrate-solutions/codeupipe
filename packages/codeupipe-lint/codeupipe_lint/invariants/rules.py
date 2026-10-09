"""Invariant rule ids, and the messages that name the fix (packages/codeupipe-lint/README.md)."""

from codeupipe_lint.anonymous_steps.finding import Finding

__all__ = ["RULES", "PARSE_ERROR", "PAYLOAD_INTERNALS", "SHARED_VALUE_MUTATION", "STATE_READ", "make_finding"]

PARSE_ERROR = "CUP-I000"
PAYLOAD_INTERNALS = "CUP-I001"
SHARED_VALUE_MUTATION = "CUP-I002"
STATE_READ = "CUP-I003"

RULES = {
    PARSE_ERROR: "parse-error",
    PAYLOAD_INTERNALS: "payload-internals",
    SHARED_VALUE_MUTATION: "shared-value-mutation",
    STATE_READ: "state-read-in-step",
}

_FIX = {
    PARSE_ERROR: "Fix the syntax error so the file can be checked.",
    PAYLOAD_INTERNALS: ("A Payload is changed through insert, remove and merge. They write in place; "
                        "for a separate Payload, use payload.copy()."),
    SHARED_VALUE_MUTATION: ("A Payload shares its nested values, so every copy of the Payload and the caller's "
                            "input change too. Copy the value first (list(...), dict(...)), change the copy, "
                            "and insert it."),
    STATE_READ: ("A Filter's result and a Valve's decision must depend only on the Payload. Put what the step "
                 "needs into the Payload, or observe State from a Tap or a Hook."),
}


def make_finding(path: str, line: int, col: int, rule: str, what: str) -> Finding:
    """A Finding whose message reads ``<what>. <fix>``."""
    return Finding(path, line, col, rule, RULES[rule], "%s. %s" % (what, _FIX[rule]), "python")
