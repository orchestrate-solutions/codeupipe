"""Where reference Taps and Hooks record what they saw.

A separate module on purpose: static lowering re-emits a top-level
``from conformance_sink import TAPS`` as an import, so every lowered step
appends to this one list. A list defined next to the ops would be *copied*
into each lowered step instead (see the known limitation in
packages/codeupipe/codeupipe/compile/filters/emit_inline_module_filter.py).
"""

TAPS = []
HOOKS = []
# The State of each run that a run_again step started, in order.
INNER_STATES = []


def reset():
    del TAPS[:]
    del HOOKS[:]
    del INNER_STATES[:]
