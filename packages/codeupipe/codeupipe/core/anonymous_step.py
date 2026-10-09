"""AnonymousStep: a step whose identity cannot be derived from the code.

Step identity is a pointer to the filter (conformance/API.md, "Step
identity"). Lambdas, closures, classes defined inside a function, filters
defined in the entry script and unnamed nested pipelines have no stable
pointer, and are not independently testable, so the runtime refuses them.
"""

__all__ = ["AnonymousStep"]


class AnonymousStep(TypeError):
    """Raised when a step has no stable identity to report."""
