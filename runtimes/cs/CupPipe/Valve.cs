namespace CupPipe;

/// <summary>
/// A filter gated by a predicate: <c>Valve(inner, predicate)</c>. When the
/// predicate is false the payload passes through unchanged and the step is
/// recorded as skipped. A Valve is identified by its inner filter; the
/// predicate is an <see cref="IPredicate"/> object, identified by its type,
/// configuration on the instance: <c>new Valve(f, new AtLeast(5))</c>.
/// </summary>
public sealed class Valve : IFilter
{
    private readonly IPredicate _predicate;

    internal IFilter Inner { get; }

    /// <summary>The predicate's identity (detail; the Valve is identified by its inner filter).</summary>
    public string PredicateSymbol { get; }

    /// <summary>Whether the last call skipped the inner filter.</summary>
    public bool LastSkipped { get; private set; }

    public Valve(IFilter inner, IPredicate predicate)
    {
        PredicateSymbol = StepIdentity.SymbolOf(predicate, "Valve predicate");
        Inner = inner;
        _predicate = predicate;
    }

    public Payload Call(Payload payload)
    {
        if (_predicate.Test(payload))
        {
            LastSkipped = false;
            return Inner.Call(payload);
        }
        LastSkipped = true;
        return payload;
    }
}
