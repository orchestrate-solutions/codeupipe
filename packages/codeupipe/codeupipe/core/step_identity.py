"""Derive a step's identity from its code (conformance/API.md, "Step identity").

A step is identified by the fully qualified symbol of the code that runs it:
``module.QualName`` of a filter's or tap's class, of a Valve's inner filter,
of a named Pipeline type, or of a module-level function. Nothing about it is
written by hand, so it cannot drift from the code it names.
"""

import sys
import types
from typing import Any

from .anonymous_step import AnonymousStep

__all__ = ["identify", "symbol_of", "predicate_symbol", "add_site"]

_FIX = "Define it at module level (a named class or a module-level def) so it has a stable identity and can be tested on its own."


def symbol_of(target: Any, what: str) -> str:
    """``module.QualName`` of a class or function, or AnonymousStep."""
    module = getattr(target, "__module__", None)
    qualname = getattr(target, "__qualname__", None)
    if not module or not qualname:
        raise AnonymousStep(f"{what} {target!r} has no module and qualified name. {_FIX}")
    if "<lambda>" in qualname:
        raise AnonymousStep(f"{what} is a lambda ({module}.{qualname}). {_FIX}")
    if "<locals>" in qualname:
        raise AnonymousStep(f"{what} {module}.{qualname} is defined inside a function. {_FIX}")
    if module == "__main__":
        raise AnonymousStep(
            f"{what} {qualname} is defined in the entry script (__main__), so its identity changes with "
            f"how the program is started and tests cannot import it. Move it into a module.")
    return f"{module}.{qualname}"


def predicate_symbol(predicate: Any) -> str:
    """The identity of a Valve predicate: an object with ``test(payload) -> bool``.

    Predicates are objects (conformance/API.md, "Valve"), identified by
    their class, with any configuration on the instance. A function (named,
    lambda or closure) is not a predicate object.
    """
    if isinstance(predicate, (types.FunctionType, types.BuiltinFunctionType, types.MethodType, type)) \
            or not callable(getattr(predicate, "test", None)):
        what = getattr(predicate, "__qualname__", None) or type(predicate).__qualname__
        raise AnonymousStep(
            f"Valve predicate {what} is not a predicate object. Declare a module-level class with "
            f"test(self, payload) -> bool (configuration on the instance) and pass an instance.")
    return symbol_of(type(predicate), "Valve predicate")


def identify(step: Any, kind: str) -> str:
    """The identity of a step, before any ``#n`` occurrence number.

    kind: "filter", "tap" or "pipeline".
    """
    from .pipeline import Pipeline  # local: pipeline imports this module
    from .valve import Valve

    if kind == "pipeline" or isinstance(step, Pipeline):
        if type(step) is Pipeline:
            raise AnonymousStep(
                "A nested pipeline must be a named Pipeline type (class UserOnboarding(Pipeline): ...), "
                "identified like a filter. A plain Pipeline() can only run at the top level.")
        return symbol_of(type(step), "Nested pipeline")
    if isinstance(step, Valve):
        return identify(step._inner, "filter")
    if isinstance(step, (type, types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
        return symbol_of(step, kind.capitalize())
    return symbol_of(type(step), kind.capitalize())


def add_site(depth: int = 2) -> str:
    """``file:line`` of the caller ``depth`` frames up: where the step was added."""
    frame = sys._getframe(depth)
    return f"{frame.f_code.co_filename}:{frame.f_lineno}"
