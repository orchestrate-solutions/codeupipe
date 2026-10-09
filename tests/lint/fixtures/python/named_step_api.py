"""Uses core/typed, whose pipeline takes hand-written step names: step
identity (and so this rule) does not apply to it. Nothing is flagged."""

from codeupipe.core.typed import TypedPipeline


def build():
    p = TypedPipeline()
    p.add_filter(lambda ctx: ctx, "inline")
    return p
