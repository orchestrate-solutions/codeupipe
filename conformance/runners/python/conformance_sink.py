"""Where reference Taps and Hooks record what they saw.

A separate module on purpose: static lowering re-emits a top-level
``from conformance_sink import TAPS`` as an import, so every lowered step
appends to this one list. A list defined next to the ops would be *copied*
into each lowered step instead (see the known limitation in
packages/codeupipe/codeupipe/lower/filters/emit_inline_module.py).
"""

TAPS = []
HOOKS = []


def reset():
    del TAPS[:]
    del HOOKS[:]
