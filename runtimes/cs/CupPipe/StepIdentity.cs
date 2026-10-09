using System.Reflection;
using System.Runtime.CompilerServices;

namespace CupPipe;

/// <summary>
/// Step identity, derived from the code (conformance/API.md, "Step identity"):
/// a type's full name (nested-type <c>+</c> shown as <c>.</c>). Compiler-
/// generated types are refused.
/// </summary>
internal static class StepIdentity
{
    private const string Fix = "Declare it as a named class, or a named method (a static method, or an instance " +
        "method on a named class when the predicate needs configuration), so it has a stable identity and can be " +
        "tested on its own.";

    private static bool IsGenerated(MemberInfo member) =>
        member.IsDefined(typeof(CompilerGeneratedAttribute), inherit: false) || member.Name.Contains('<');

    private static string TypeName(Type type) => (type.FullName ?? type.Name).Replace('+', '.');

    public static string SymbolOf(object value, string what)
    {
        var type = value.GetType();
        if (IsGenerated(type))
            throw new AnonymousStep($"{what} is a compiler-generated type ({type.Name}). {Fix}");
        return TypeName(type);
    }

    /// <summary>A step's identity, before any #n occurrence number.</summary>
    public static string Identify(object step, string what) =>
        step is Valve valve ? SymbolOf(valve.Inner, "Filter") : SymbolOf(step, what);
}
