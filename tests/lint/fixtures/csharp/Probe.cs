// Step-identity probe cases, with Describe(label, f) replaced by a
// pipeline add call: the probe's cases as lint fixtures.
using System;
using System.Collections.Generic;

namespace App.Filters
{
    public interface IFilter { Dictionary<string, object?> Call(Dictionary<string, object?> p); }
    public sealed class Validate : IFilter { public Dictionary<string, object?> Call(Dictionary<string, object?> p) => p; }
    public static class Funcs { public static bool Normalize(Dictionary<string, object?> p) => true; }
}

namespace App.Probe
{
    using App.Filters;

    public static class Program
    {
        static Func<Dictionary<string, object?>, bool> MakeClosure(string k) => p => p.ContainsKey(k);

        public static void Main()
        {
            var p = new Pipeline();
            p.AddFilter(new Validate(), "class instance");
            p.AddFilter(new Validate(), "same class again");
            p.AddFilter(new Valve("v", new Validate(), Funcs.Normalize), "method group");
            p.AddFilter(new Valve("v", new Validate(), (Func<Dictionary<string, object?>, bool>)(x => true)), "lambda"); // expect: CUP-A001
            p.AddFilter(new Valve("v", new Validate(), MakeClosure("x")), "closure"); // expect: CUP-A001
        }
    }
}
