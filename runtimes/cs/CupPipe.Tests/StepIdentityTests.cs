using CupPipe;
using Xunit;

namespace CupPipe.Tests;

// Step identity (conformance/API.md): a step is identified by its type's full
// name, #n from its second use; no names. Lambda predicates are refused.

public sealed class IdInc : IFilter
{
    public Payload Call(Payload p) => p.Insert("n", Convert.ToInt32(p.Get("n", 0)) + 1);
}

public sealed class IdBoom : IFilter
{
    public Payload Call(Payload p) => throw new InvalidOperationException("boom");
}

public sealed class IdAudit : ITap
{
    public void Observe(Payload p) { }
}

/// <summary>A predicate object: identified by its type.</summary>
public sealed class IdIsOn : IPredicate
{
    public bool Test(Payload p) => p.Get("on") is true;
}

/// <summary>A configurable predicate: its setting lives on the instance.</summary>
public sealed class IdAtLeast(int n) : IPredicate
{
    public bool Test(Payload p) => Convert.ToInt32(p.Get("n", 0)) >= n;
}

public sealed class IdOnboarding : Pipeline
{
    public IdOnboarding() => AddFilter(new IdInc());
}

public sealed class IdRecord : Hook
{
    public List<string> Events { get; } = new();
    public override void Before(string? step, Payload p) => Events.Add("before:" + step);
    public override void After(string? step, Payload p) => Events.Add("after:" + step);
    public override void OnError(string? step, Exception e, Payload p) => Events.Add("error:" + step);
}

public class StepIdentityTests
{
    private const string Here = "CupPipe.Tests.";

    [Fact]
    public void StateReportsTheFullTypeName()
    {
        var p = new Pipeline().AddFilter(new IdInc());
        p.Run(new Payload());
        Assert.Equal(new[] { Here + "IdInc" }, p.State.Executed);
    }

    [Fact]
    public void ReuseIsNumberedFromTheSecondOccurrence()
    {
        var p = new Pipeline().AddFilter(new IdInc()).AddFilter(new IdInc()).AddFilter(new IdInc());
        Assert.Equal(new[] { Here + "IdInc", Here + "IdInc#2", Here + "IdInc#3" }, p.Identities);
    }

    [Fact]
    public void NestedTypesUseDotsNotPlus()
    {
        var p = new Pipeline().AddFilter(new Holder.Inner());
        Assert.Equal(new[] { Here + "StepIdentityTests.Holder.Inner" }, p.Identities);
    }

    public static class Holder
    {
        public sealed class Inner : IFilter { public Payload Call(Payload p) => p; }
    }

    [Fact]
    public void TapsAndHooksSeeIdentities()
    {
        var hook = new IdRecord();
        var p = new Pipeline().AddFilter(new IdInc()).AddTap(new IdAudit()).AddFilter(new IdBoom()).UseHook(hook);
        Assert.Throws<InvalidOperationException>(() => p.Run(new Payload()));
        Assert.Equal(new[] { Here + "IdInc", Here + "IdAudit" }, p.State.Executed);
        Assert.Equal(new[] { "before:", "before:" + Here + "IdInc", "after:" + Here + "IdInc",
            "before:" + Here + "IdBoom", "error:" + Here + "IdBoom", "error:" }, hook.Events);
    }

    [Fact]
    public void AValveIsIdentifiedByItsInnerFilter()
    {
        var p = new Pipeline().AddFilter(new Valve(new IdInc(), new IdIsOn()));
        p.Run(new Payload());
        Assert.Equal(new[] { Here + "IdInc" }, p.State.Skipped);
    }

    [Fact]
    public void APredicateObjectCarriesConfiguration()
    {
        var v = new Valve(new IdInc(), new IdAtLeast(5));
        Assert.Equal(Here + "IdAtLeast", v.PredicateSymbol);
        var p = new Pipeline().AddFilter(v);
        Assert.Equal(6, p.Run(new Payload(new() { ["n"] = 5 })).Get<int>("n"));
    }

    [Fact]
    public void ANamedPipelineSubclassNestsAsOneStep()
    {
        var outer = new Pipeline().AddFilter(new IdInc()).AddPipeline(new IdOnboarding());
        Assert.Equal(2, outer.Run(new Payload()).Get<int>("n"));
        Assert.Equal(new[] { Here + "IdInc", Here + "IdOnboarding" }, outer.State.Executed);
    }

    [Fact]
    public void TheAddSiteIsRecorded()
    {
        var p = new Pipeline().AddFilter(new IdInc());
        Assert.Matches(@"StepIdentityTests\.cs:\d+$", p.StepSites[Here + "IdInc"]);
    }

    // A lambda or method group is not an IPredicate: passing one to Valve is a
    // compile error, so there is no runtime refusal to test.

    [Fact]
    public void APlainPipelineCannotBeNested()
    {
        var e = Assert.Throws<AnonymousStep>(() => new Pipeline().AddPipeline(new Pipeline().AddFilter(new IdInc())));  // cup: allow-anonymous (a deliberate refusal test)
        Assert.Contains("named Pipeline subclass", e.Message);
    }
}
