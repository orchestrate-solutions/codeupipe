"""LoweringMode: the export pipeline's Valve predicate.

A predicate object (conformance/API.md, "Valve"): true when the export's
``lowering`` matches this instance's mode. ``inline=True`` selects the
flattened layout; ``inline=False`` the per-step layout (the default when
``lowering`` is absent).
"""

__all__ = ["LoweringMode"]


class LoweringMode:
    def __init__(self, inline: bool):
        self.inline = inline

    def test(self, payload) -> bool:
        return (payload.get("lowering") == "inline") == self.inline
