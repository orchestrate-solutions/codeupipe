// Named steps the C# analyzer must NOT flag.
using System;
using System.Linq;
using CupPipe;

namespace App.Filters
{
    public sealed class Named : IFilter { public Payload Call(Payload p) => p; }
    public sealed class Audit : ITap { public void Observe(Payload p) { } }

    public sealed class Onboarding : Pipeline
    {
        public Onboarding() { AddFilter(new Named(), "n"); }
    }

    public static class Predicates
    {
        public static bool IsOn(Payload p) => true;
    }

    public static class Builder
    {
        static IFilter MakeNamed() => new Named();

        public static Pipeline Build(IFilter[] steps, Func<Payload, bool> pred)
        {
            var text = "p.AddFilter(x => x, \"lambda\")";
            var verbatim = @"new Valve(""v"", x, _ => true)";
            var p = new Pipeline(); // a plain pipeline at the top level is fine
            p.AddFilter(new Named(), "a");
            p.AddTap(new Audit(), "audit");
            p.AddFilter(new Valve("v", new Named(), Predicates.IsOn), "method group");
            p.AddFilter(new Valve("v", new Named(), pred), "parameter");
            p.AddPipeline(new Onboarding(), "onboarding");
            p.AddFilter(MakeNamed(), "factory");
            foreach (var s in steps) p.AddFilter(s, "loop");
            var doubled = steps.Select(s => s).ToArray(); // a lambda that is not a step
            Console.WriteLine(text + verbatim + doubled.Length);
            return p;
        }
    }
}
