namespace CupPipe;

/// <summary>
/// A <see cref="Valve"/>'s condition (conformance/API.md, "Valve"): an object
/// with <c>Test</c>, identified by its type like a step, configuration on the
/// instance (<c>new AtLeast(5)</c>). A lambda or method group is not an
/// IPredicate, so it does not compile.
/// </summary>
public interface IPredicate
{
    bool Test(Payload payload);
}
