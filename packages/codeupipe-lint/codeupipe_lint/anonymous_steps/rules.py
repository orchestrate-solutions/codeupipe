"""Rule ids, and the messages that name the fix (packages/codeupipe-lint/README.md).

The runtime reports a step by the name of its class
(packages/codeupipe/codeupipe/core/step_label.py).
"""

from typing import Optional

from .finding import Finding

__all__ = ["RULES", "LAMBDA", "LOCAL_FUNCTION", "LOCAL_TYPE", "UNNAMED_PIPELINE",
           "FUNCTION_PREDICATE", "PARSE_ERROR", "make_finding"]

LAMBDA = "CUP-A001"
LOCAL_FUNCTION = "CUP-A002"
LOCAL_TYPE = "CUP-A003"
UNNAMED_PIPELINE = "CUP-A005"
FUNCTION_PREDICATE = "CUP-A008"
PARSE_ERROR = "CUP-A000"

RULES = {
    PARSE_ERROR: "parse-error",
    LAMBDA: "lambda-step",
    LOCAL_FUNCTION: "local-function-step",
    LOCAL_TYPE: "local-type-step",
    UNNAMED_PIPELINE: "unnamed-pipeline-step",
    FUNCTION_PREDICATE: "function-predicate",
}

_TAIL = " so it has a name in State and can be tested on its own."

# Steps and Valve predicates are named types (predicates are objects with
# test(payload), conformance/API.md, "Valve").
_FIX = {
    "python": "Define it at module level as a named class (a Valve predicate: a class with test(self, payload))" + _TAIL,
}

_PIPELINE_EXAMPLE = {
    "python": "class UserOnboarding(Pipeline): ...",
}


def _fix(lang: str, rule: str) -> str:
    if rule == UNNAMED_PIPELINE:
        return ("A nested pipeline must be a named pipeline type (%s), named like a filter. "
                "A plain Pipeline can only run at the top level." % _PIPELINE_EXAMPLE[lang])
    if rule == FUNCTION_PREDICATE:
        return ("Valve predicates are objects (conformance/API.md, \"Valve\"): wrap the condition in a "
                "named class with test(payload), configuration on the instance, and pass an instance.")
    if rule == PARSE_ERROR:
        return "Fix the syntax error so the file can be checked."
    return _FIX[lang]


def make_finding(lang: str, path: str, line: int, col: int, rule: str, role: str, what: str,
                 call_line: Optional[int] = None) -> Finding:
    """A Finding whose message reads ``<Role> <what>. <fix>``; ``what`` starts with its verb
    (``is a lambda``, ```bound` is a lambda``)."""
    message = "%s %s. %s" % (role, what, _fix(lang, rule))
    return Finding(path, line, col, rule, RULES[rule], message, lang,
                   call_line if call_line != line else None)
