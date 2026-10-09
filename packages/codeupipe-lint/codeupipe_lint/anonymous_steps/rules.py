"""Rule ids, and the messages that name the fix (packages/codeupipe-lint/README.md).

The wording mirrors the runtimes' AnonymousStep refusals
(packages/codeupipe/codeupipe/core/step_identity.py, runtimes/ts/src/step_identity.ts).
"""

from typing import Optional

from .finding import Finding

__all__ = ["RULES", "LAMBDA", "LOCAL_FUNCTION", "LOCAL_TYPE", "ANONYMOUS_TYPE", "UNNAMED_PIPELINE",
           "ENTRY_SCRIPT", "FREE_FUNCTION", "FUNCTION_PREDICATE", "PARSE_ERROR", "make_finding"]

LAMBDA = "CUP-A001"
LOCAL_FUNCTION = "CUP-A002"
LOCAL_TYPE = "CUP-A003"
ANONYMOUS_TYPE = "CUP-A004"
UNNAMED_PIPELINE = "CUP-A005"
ENTRY_SCRIPT = "CUP-A006"
FREE_FUNCTION = "CUP-A007"
FUNCTION_PREDICATE = "CUP-A008"
PARSE_ERROR = "CUP-A000"

RULES = {
    PARSE_ERROR: "parse-error",
    LAMBDA: "lambda-step",
    LOCAL_FUNCTION: "local-function-step",
    LOCAL_TYPE: "local-type-step",
    ANONYMOUS_TYPE: "anonymous-type-step",
    UNNAMED_PIPELINE: "unnamed-pipeline-step",
    ENTRY_SCRIPT: "entry-script-step",
    FREE_FUNCTION: "free-function-step",
    FUNCTION_PREDICATE: "function-predicate",
}

_TAIL = " so it has a stable identity and can be tested on its own."

# Steps and Valve predicates are named types (predicates are objects with
# test(payload), conformance/API.md, "Valve").
_FIX = {
    "python": "Define it at module level as a named class (a Valve predicate: a class with test(self, payload))" + _TAIL,
    "go": "Declare it at package level as a named type (a Valve predicate: a type with Test(Payload) bool)" + _TAIL,
    "ts": "Declare it as a top-level class (a Valve predicate: a class implementing Predicate)" + _TAIL,
    "rust": "Declare it at module level as a named type (a Valve predicate: a type implementing Predicate)" + _TAIL,
    "cpp": "Declare it at namespace scope as a named struct or class (a Valve predicate: a type with test())" + _TAIL,
    "kotlin": "Declare it at top level as a named class or object (a Valve predicate: implements Predicate)" + _TAIL,
    "csharp": "Declare it as a named class (a Valve predicate: a class implementing IPredicate)" + _TAIL,
}

_PIPELINE_EXAMPLE = {
    "python": "class UserOnboarding(Pipeline): ...",
    "ts": "class UserOnboarding extends Pipeline { ... }",
    "go": "type UserOnboarding struct{ *codeupipe.Pipeline }",
    "rust": "struct UserOnboarding wrapping a Pipeline",
    "cpp": "struct UserOnboarding : Pipeline { ... }",
    "kotlin": "class UserOnboarding : Pipeline()",
    "csharp": "class UserOnboarding : Pipeline",
}


def _fix(lang: str, rule: str) -> str:
    if rule == UNNAMED_PIPELINE:
        return ("A nested pipeline must be a named pipeline type (%s), identified like a filter. "
                "A plain Pipeline can only run at the top level." % _PIPELINE_EXAMPLE[lang])
    if rule == ENTRY_SCRIPT:
        return ("Its identity would be __main__.X, which changes with how the program is started, "
                "and tests cannot import it. Move it into a module.")
    if rule == FREE_FUNCTION:
        return ("A free function has no derivable name (a function pointer carries only its signature); "
                "C++ filters must be types. Wrap it in a struct declared at namespace scope.")
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
