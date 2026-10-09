namespace CupPipe;

/// <summary>
/// A step whose identity cannot be derived from the code. Step identity is a
/// pointer to the filter (conformance/API.md, "Step identity"); a lambda or
/// closure predicate (compiler-generated) or a plain <see cref="Pipeline"/>
/// nested as a step has none and is not independently testable, so it is
/// refused when added.
/// </summary>
public sealed class AnonymousStep(string message) : ArgumentException(message);
