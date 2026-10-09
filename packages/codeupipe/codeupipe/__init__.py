"""codeupipe: the seven primitives, runnable two ways.

``codeupipe.core`` is the dynamic runtime. ``codeupipe.lower`` exports a
pipeline as plain code with no framework import.
"""

from .core import *  # noqa: F401,F403
from .core import __all__  # noqa: F401
