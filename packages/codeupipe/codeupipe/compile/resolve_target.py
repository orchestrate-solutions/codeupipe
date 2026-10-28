"""Turn ``module:name`` into the Pipeline it names."""

from __future__ import annotations

import importlib
import inspect

from codeupipe.core import Pipeline

__all__ = ["TargetError", "resolve_target"]


class TargetError(Exception):
    """The ``module:name`` given does not lead to a Pipeline."""


# cup: allow-plain used by the entry of the program: it finds the pipeline that an argument names
def resolve_target(spec: str) -> Pipeline:
    """``name`` may be a Pipeline, or anything callable with no arguments that
    returns one: a builder function or a named Pipeline type."""
    module_name, colon, attr = spec.partition(":")
    if not (colon and module_name and attr):
        raise TargetError(f"{spec!r}: name the pipeline as module:name, for example app.pipelines:checkout")
    try:
        module = importlib.import_module(module_name)
    except Exception as error:
        raise TargetError(f"cannot import {module_name}: {error}") from error
    if not hasattr(module, attr):
        raise TargetError(f"{module_name} has no attribute {attr}")

    target = getattr(module, attr)
    if not isinstance(target, Pipeline) and callable(target):
        try:
            inspect.signature(target).bind()
        except TypeError as error:
            raise TargetError(f"{spec} takes arguments, so it cannot be built from the command line") from error
        target = target()
    if not isinstance(target, Pipeline):
        raise TargetError(f"{spec} is not a Pipeline (it is a {type(target).__name__})")
    return target
