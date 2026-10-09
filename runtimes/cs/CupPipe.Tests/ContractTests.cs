using CupPipe;
using Xunit;

namespace CupPipe.Tests;

/// <summary>
/// The CUP API contract, C# side (conformance/API.md). Cross-runtime
/// semantics are in conformance/cases; these pin the C# spellings.
/// </summary>
public class ContractTests
{
    private sealed class Set(string key, object? value) : IFilter
    {
        public Payload Call(Payload p) => p.Insert(key, value);
    }

    private sealed class Open : IPredicate { public bool Test(Payload p) => true; }
    private sealed class Shut : IPredicate { public bool Test(Payload p) => false; }

    private class SubPipeline : Pipeline { }

    private sealed class Inc : IFilter
    {
        public Payload Call(Payload p) => p.Insert("n", Convert.ToInt32(p.Get("n", 0)) + 1);
    }

    private sealed class Boom : IFilter
    {
        public Payload Call(Payload p) => throw new InvalidOperationException("boom");
    }

    private sealed class Record : Hook
    {
        public List<string> Events { get; } = new();
        public override void Before(string? step, Payload p) => Events.Add("before:" + step);
        public override void After(string? step, Payload p) => Events.Add("after:" + step);
        public override void OnError(string? step, Exception e, Payload p) => Events.Add("error:" + step);
    }

    [Fact]
    public void Valve_RunsWhenOpen_SkipsWhenClosed()
    {
        var p = new Pipeline()
            .AddFilter(new Valve(new Set("x", 1), new Open()))
            .AddFilter(new Valve(new Set("y", 1), new Shut()));

        var result = p.Run(new Payload());

        Assert.True(result.Has("x"));
        Assert.False(result.Has("y"));
        Assert.Equal(new[] { "CupPipe.Tests.ContractTests.Set" }, p.State.Executed);
        Assert.Equal(new[] { "CupPipe.Tests.ContractTests.Set#2" }, p.State.Skipped);
    }

    [Fact]
    public void NestedPipeline_IsOneStep()
    {
        var inner = new SubPipeline().AddFilter(new Inc());
        var p = new Pipeline().AddFilter(new Inc()).AddPipeline(inner);

        var result = p.Run(new Payload(new() { ["n"] = 0 }));

        Assert.Equal(2, Convert.ToInt32(result.Get("n")));
        Assert.Equal(new[] { "CupPipe.Tests.ContractTests.Inc", "CupPipe.Tests.ContractTests.SubPipeline" }, p.State.Executed);
    }

    [Fact]
    public void Hooks_ReceiveStepIdentities()
    {
        var hook = new Record();
        var p = new Pipeline().AddFilter(new Inc()).AddFilter(new Boom()).UseHook(hook);

        Assert.Throws<InvalidOperationException>(() => p.Run(new Payload(new() { ["n"] = 0 })));

        const string a = "CupPipe.Tests.ContractTests.Inc", b = "CupPipe.Tests.ContractTests.Boom";
        Assert.Equal(new[] { "before:", "before:" + a, "after:" + a, "before:" + b, "error:" + b, "error:" }, hook.Events);
    }



    [Fact]
    public void Payload_RemoveAndHas()
    {
        var p = new Payload(new() { ["a"] = null, ["b"] = 2 });

        Assert.True(p.Has("a"));
        Assert.False(p.Has("zz"));
        Assert.Equal(new Dictionary<string, object?> { ["b"] = 2 }, p.Remove("a").ToDict());
        Assert.True(p.Has("a")); // Remove returned a new payload
    }

    [Fact]
    public void MutablePayload_SetsAndRemovesInPlace()
    {
        var m = new Payload(new() { ["a"] = 1 }).WithMutation();
        m.Set("k", "v");
        m.Remove("a");

        Assert.Equal(new Dictionary<string, object?> { ["k"] = "v" }, m.ToImmutable().ToDict());
    }

    [Fact]
    public void TypedGet_OfTheWrongType_FailsLoudly()
    {
        var p = new Payload(new() { ["s"] = "not a number" });

        Assert.ThrowsAny<Exception>(() => p.Get<int>("s"));
        Assert.Equal(5, p.Get<int>("missing", 5)); // missing still yields the default
    }
}
