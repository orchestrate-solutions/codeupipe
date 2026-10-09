"""Imports both a named-step variant and the identity core: checked."""

from codeupipe.core.typed import TypedPipeline
from codeupipe import Pipeline


def build():
    p = Pipeline()
    p.add_filter(lambda payload: payload)  # expect: CUP-A001
    return p, TypedPipeline
