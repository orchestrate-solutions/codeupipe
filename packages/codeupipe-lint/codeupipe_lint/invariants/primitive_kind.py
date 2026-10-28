"""primitive_kind: which primitive a class is, read from its shape.

Python steps are duck-typed, so the shape is the evidence:

* a ``Pipeline`` subclass is a pipeline;
* a ``Hook`` subclass, or a class with ``before``, ``after`` and
  ``on_error``, is a hook;
* a class with ``call(self, payload)`` is a filter;
* a class with ``observe(self, payload)`` is a tap;
* a class with ``test(self, payload)`` is a predicate.

``call``, ``observe`` and ``test`` count only with exactly one argument
after ``self``, so a ``unittest`` method or an unrelated ``call(a, b)`` is
not mistaken for a step.
"""

import ast

__all__ = ["primitive_kind", "is_test_file"]

_BY_METHOD = (("call", "Filter"), ("observe", "Tap"), ("test", "predicate"))
_HOOK_METHODS = {"before", "after", "on_error"}
_HOOK_BASES = {"Hook", "AsyncHook"}


# cup: allow-plain shared by the analysis Filters: it says which primitive a class is, from its shape
def _base_names(node):
    return {base.id if isinstance(base, ast.Name) else getattr(base, "attr", "") for base in node.bases}


def _takes_only_the_payload(method) -> bool:
    arguments = method.args.posonlyargs + method.args.args
    return (len(arguments) == 2 and arguments[0].arg in ("self", "cls")
            and not method.args.vararg and not method.args.kwonlyargs and not method.args.kwarg)


# cup: allow-plain shared by the analysis Filters: it says which primitive a class is, from its shape
def primitive_kind(node):
    """"Pipeline", "Hook", "Filter", "Tap" or "predicate"; None for any other class."""
    methods = {member.name: member for member in node.body
               if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))}
    bases = _base_names(node)
    if "Pipeline" in bases:
        return "Pipeline"
    if bases & _HOOK_BASES or _HOOK_METHODS <= set(methods):
        return "Hook"
    for name, kind in _BY_METHOD:
        if name in methods and _takes_only_the_payload(methods[name]):
            return kind
    return None


def is_test_file(path: str) -> bool:
    """A test, a conftest, or anything under a ``tests`` directory."""
    parts = path.replace("\\", "/").split("/")
    name = parts[-1]
    return "tests" in parts[:-1] or name.startswith("test_") or name == "conftest.py"
