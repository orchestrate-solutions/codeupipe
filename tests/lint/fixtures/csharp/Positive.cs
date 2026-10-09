// Anonymous steps the C# analyzer must flag (expect: comments name the rule).
using System;
using CupPipe;

namespace App.Filters
{
    public sealed class Named : IFilter { public Payload Call(Payload p) => p; }

    public sealed class FuncFilter : IFilter
    {
        private readonly Func<Payload, Payload> _f;
        public FuncFilter(Func<Payload, Payload> f) { _f = f; }
        public Payload Call(Payload p) => _f(p);
    }

    public static class Builder
    {
        static bool IsOn(Payload p) => true;

        static Func<Payload, bool> MakeClosure(string k) => p => p.Get(k) != null;

        static IFilter FilterFor(string op) => op switch
        {
            "id" => new FuncFilter(p => p),
            var other => throw new NotSupportedException(other),
        };

        static IFilter Wrapped()
        {
            return new FuncFilter(delegate (Payload x) { return x; });
        }

        static Pipeline BuildChild()
        {
            return new Pipeline().AddFilter(new Named(), "n");
        }

        public static Pipeline Build()
        {
            bool LocalPred(Payload p) => true;
            static Payload LocalStep(Payload p) { return p; }

            var p = new Pipeline();
            p.AddFilter(new FuncFilter(x => x), "lambda"); // expect: CUP-A001
            p.AddFilter(new FuncFilter(delegate (Payload x) { return x; }), "delegate"); // expect: CUP-A001
            p.AddFilter(new Valve("v", new Named(), _ => true), "valve"); // expect: CUP-A001
            p.AddFilter(new Valve("v", new Named(), LocalPred), "local fn"); // expect: CUP-A002
            p.AddFilter(new Valve("v", new Named(), MakeClosure("k")), "factory"); // expect: CUP-A001
            p.AddTap(new { Observe = 1 }, "anonymous type"); // expect: CUP-A004
            p.AddFilter(FilterFor("id"), "switch factory"); // expect: CUP-A001
            p.AddFilter(Wrapped(), "block factory"); // expect: CUP-A001
            p.AddFilter(new Valve("v", new Named(), predicate: x => true), "named argument"); // expect: CUP-A001

            Func<Payload, bool> pred = x => false;
            p.AddFilter(new Valve("v", new Named(), pred), "bound"); // expect: CUP-A001
            var wrapped = new FuncFilter(LocalStep);
            p.AddFilter(new FuncFilter(LocalStep), "local step"); // (wrapped: not seen, see KnownLimits)

            var inner = new Pipeline().AddFilter(new Named(), "inner");
            p.AddPipeline(inner, "inner"); // expect: CUP-A005
            p.AddPipeline(new Pipeline(), "empty"); // expect: CUP-A005
            p.AddPipeline(BuildChild(), "child"); // expect: CUP-A005
            return p;
        }
    }
}
