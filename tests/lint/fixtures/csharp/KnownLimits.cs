// What the lexical scan cannot see (packages/codeupipe-lint/README.md). Unflagged lines are
// false negatives; an expect comment marked (false positive) is one.
using System;
using CupPipe;

public sealed class Named : IFilter { public Payload Call(Payload p) => p; }
public sealed class Options : IFilter
{
    public Options(Func<int, int> configure) { }
    public Payload Call(Payload p) => p;
}

public static class Builder
{
    public static Pipeline Build()
    {
        static Payload LocalStep(Payload p) => p;
        var p = new Pipeline();
        // A local function wrapped in an adapter: the adapter is a named class.
        p.AddFilter(new FuncFilter(LocalStep), "wrapped local function");
        // A factory in another file: its return type is unknown here.
        p.AddFilter(Factories.MakeLambdaFilter(), "remote");
        // `=>` anywhere in the argument counts, even as a named filter's option.
        p.AddFilter(new Options(x => x + 1), "configured"); // expect: CUP-A001 (false positive)
        return p;
    }
}
