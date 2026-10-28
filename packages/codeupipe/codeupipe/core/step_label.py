"""The label of a step: the name of its class.

State and Hooks report a step by this label. It comes from the code, so it
cannot differ from the code. A Valve has the label of its Filter.
"""

from typing import Any

__all__ = ["label_of"]


# cup: allow-plain a part of the Pipeline primitive: it gives a step its label
def label_of(step: Any) -> str:
    """The class name of ``step``; for a Valve, of its Filter."""
    inner = getattr(step, "_inner", None)
    if inner is not None and hasattr(step, "_predicate"):  # a Valve
        return label_of(inner)
    if isinstance(step, type):
        return step.__name__
    return type(step).__name__
