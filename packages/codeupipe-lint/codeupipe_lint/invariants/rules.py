"""Invariant rule ids, and the messages that name the fix (packages/codeupipe-lint/README.md)."""

from codeupipe_lint.anonymous_steps.finding import Finding

__all__ = ["RULES", "PARSE_ERROR", "PAYLOAD_INTERNALS", "SHARED_VALUE_MUTATION", "STATE_READ",
           "WRITE_OUTSIDE_FILTER", "ONE_PRIMITIVE_PER_FILE", "PRIMITIVE_FILE_NAME",
           "PRIMITIVE_ROLE_SUFFIX", "LOGIC_OUTSIDE_PRIMITIVE", "MARKER_ALLOWS_NOTHING", "WARNINGS", "make_finding"]

PARSE_ERROR = "CUP-I000"
PAYLOAD_INTERNALS = "CUP-I001"
SHARED_VALUE_MUTATION = "CUP-I002"
STATE_READ = "CUP-I003"
WRITE_OUTSIDE_FILTER = "CUP-I004"
ONE_PRIMITIVE_PER_FILE = "CUP-I005"
PRIMITIVE_FILE_NAME = "CUP-I006"
PRIMITIVE_ROLE_SUFFIX = "CUP-I007"
LOGIC_OUTSIDE_PRIMITIVE = "CUP-I008"
MARKER_ALLOWS_NOTHING = "CUP-I009"

# The rules whose findings are warnings.
WARNINGS = frozenset([LOGIC_OUTSIDE_PRIMITIVE, MARKER_ALLOWS_NOTHING])
_SEVERITY = {rule: "warning" for rule in WARNINGS}

RULES = {
    PARSE_ERROR: "parse-error",
    PAYLOAD_INTERNALS: "payload-internals",
    SHARED_VALUE_MUTATION: "shared-value-mutation",
    STATE_READ: "state-read-in-step",
    WRITE_OUTSIDE_FILTER: "write-outside-filter",
    ONE_PRIMITIVE_PER_FILE: "one-primitive-per-file",
    PRIMITIVE_FILE_NAME: "primitive-file-name",
    PRIMITIVE_ROLE_SUFFIX: "primitive-role-suffix",
    LOGIC_OUTSIDE_PRIMITIVE: "logic-outside-primitive",
    MARKER_ALLOWS_NOTHING: "marker-allows-nothing",
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
    WRITE_OUTSIDE_FILTER: ("Only a Filter writes to the Payload, and nothing at run time stops this write. "
                           "Put the write in a Filter, or write to payload.copy()."),
    ONE_PRIMITIVE_PER_FILE: ("Give each Filter, Predicate, Tap, Hook and named Pipeline its own file, so it can "
                             "be tested alone and used again. The pipeline file is where they come together."),
    PRIMITIVE_FILE_NAME: ("The file name of a primitive is its class name in snake_case, so one name gives "
                          "the other."),
    PRIMITIVE_ROLE_SUFFIX: ("A primitive's class name ends with its role (Filter, Tap, Hook, Predicate, "
                            "Pipeline), so the name tells what the class is."),
    LOGIC_OUTSIDE_PRIMITIVE: ("Write it as a primitive, so that the pipeline has the logic and it can be tested "
                              "as a step. For logic that must be plain code, say why: # cup: allow-plain <reason>"),
    MARKER_ALLOWS_NOTHING: ("Remove it, or put it on the line of the finding that it is for. A comment that "
                            "allows nothing says that the code has an exception that it does not have."),
}


def make_finding(path: str, line: int, col: int, rule: str, what: str) -> Finding:
    """A Finding whose message reads ``<what>. <fix>``."""
    return Finding(path, line, col, rule, RULES[rule], "%s. %s" % (what, _FIX[rule]), "python",
                   severity=_SEVERITY.get(rule))
