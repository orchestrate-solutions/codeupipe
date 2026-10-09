namespace CupPipe.Tests;

/// <summary>Tests for Pipeline: filter execution, taps, hooks, state, contracts.</summary>
public class PipelineTests
{
    // ── Test Filters ────────────────────────────────────────────────

    private class AddOneFilter : IFilter
    {
        public Payload Call(Payload payload)
            => payload.Insert("x", payload.Get<int>("x") + 1);
    }

    private class UpperFilter : IFilter
    {
        public Payload Call(Payload payload)
            => payload.Insert("name", payload.Get<string>("name")!.ToUpper());
    }

    private class BoomFilter : IFilter
    {
        public Payload Call(Payload payload)
            => throw new InvalidOperationException("boom");
    }

    // ── Test Taps ───────────────────────────────────────────────────

    private class RecordTap : ITap
    {
        public List<Dictionary<string, object?>> Seen { get; } = new();
        public void Observe(Payload payload) => Seen.Add(payload.ToDict());
    }

    // ── Test Hooks ──────────────────────────────────────────────────

    private class RecordHook : Hook
    {
        public List<string> Events { get; } = new();
        public override void Before(string? f, Payload p) => Events.Add("before");
        public override void After(string? f, Payload p) => Events.Add("after");
        public override void OnError(string? f, Exception e, Payload p) => Events.Add("on_error");
    }

    // ── Basic execution ─────────────────────────────────────────────

    [Fact]
    public void SingleFilter()
    {
        var sp = new Pipeline().AddFilter(new AddOneFilter());
        var result = sp.Run(new Payload(new() { ["x"] = 10 }));
        Assert.Equal(11, result.Get<int>("x"));
    }

    [Fact]
    public void MultipleFilters_Sequential()
    {
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .AddFilter(new AddOneFilter())
            .AddFilter(new AddOneFilter());
        var result = sp.Run(new Payload(new() { ["x"] = 0 }));
        Assert.Equal(3, result.Get<int>("x"));
    }

    [Fact]
    public void State_TracksExecution()
    {
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .AddFilter(new UpperFilter());
        sp.Run(new Payload(new() { ["x"] = 1, ["name"] = "alice" }));
        Assert.Equal(new[] { "CupPipe.Tests.PipelineTests.AddOneFilter", "CupPipe.Tests.PipelineTests.UpperFilter" }, sp.State.Executed);
    }

    [Fact]
    public void Returns_PayloadType()
    {
        var sp = new Pipeline().AddFilter(new AddOneFilter());
        var result = sp.Run(new Payload(new() { ["x"] = 0 }));
        Assert.IsType<Payload>(result);
    }

    // ── Taps ────────────────────────────────────────────────────────

    [Fact]
    public void Tap_Observes()
    {
        var tap = new RecordTap();
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .AddTap(tap);
        sp.Run(new Payload(new() { ["x"] = 5 }));
        Assert.Single(tap.Seen);
        Assert.Equal(6, tap.Seen[0]["x"]); // sees post-filter payload
    }

    [Fact]
    public void Tap_StateTracked()
    {
        var sp = new Pipeline().AddTap(new RecordTap());
        sp.Run(new Payload(new() { ["x"] = 1 }));
        Assert.Contains("CupPipe.Tests.PipelineTests.RecordTap", sp.State.Executed);
    }

    // ── Hooks ───────────────────────────────────────────────────────

    [Fact]
    public void Hooks_BeforeAfterFire()
    {
        var hook = new RecordHook();
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .UseHook(hook);
        sp.Run(new Payload(new() { ["x"] = 0 }));
        Assert.True(hook.Events.Count(e => e == "before") >= 2); // pipeline + filter
        Assert.True(hook.Events.Count(e => e == "after") >= 2);
    }

    [Fact]
    public void Hooks_OnErrorFires()
    {
        var hook = new RecordHook();
        var sp = new Pipeline()
            .AddFilter(new BoomFilter())
            .UseHook(hook);
        Assert.Throws<InvalidOperationException>(() =>
            sp.Run(new Payload(new() { ["x"] = 0 })));
        Assert.Contains("on_error", hook.Events);
    }

    // On a failure, OnError fires for the failing step and then for the
    // pipeline (null), mirroring Before/After, which fire at both levels.
    // Same contract in every runtime: conformance/cases/hook.json.
    private class NamedHook : Hook
    {
        public List<string> Events { get; } = new();
        public override void Before(string? step, Payload p) => Events.Add("before:" + step);
        public override void After(string? step, Payload p) => Events.Add("after:" + step);
        public override void OnError(string? step, Exception e, Payload p) => Events.Add("error:" + step);
    }

    [Fact]
    public void Hooks_OnErrorFiresForTheStepThenThePipeline()
    {
        var a = new AddOneFilter();
        var b = new BoomFilter();
        var hook = new NamedHook();
        var sp = new Pipeline().AddFilter(a).AddFilter(b).UseHook(hook);

        Assert.Throws<InvalidOperationException>(() => sp.Run(new Payload(new() { ["x"] = 0 })));

        const string a1 = "CupPipe.Tests.PipelineTests.AddOneFilter", b1 = "CupPipe.Tests.PipelineTests.BoomFilter";
        Assert.Equal(new[] { "before:", "before:" + a1, "after:" + a1, "before:" + b1, "error:" + b1, "error:" }, hook.Events);
    }

    // Plane B: a Tap failure never halts the pipeline. The exception is
    // recorded in PipelineState.Errors under the Tap's name and the Tap still
    // counts as executed. Same contract in every runtime:
    // conformance/cases/tap.json.
    private class BoomTap : ITap
    {
        public void Observe(Payload payload) => throw new InvalidOperationException("sink down");
    }

    [Fact]
    public void Tap_FailureDoesNotHaltThePipeline()
    {
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .AddTap(new BoomTap())
            .AddFilter(new AddOneFilter());

        var result = sp.Run(new Payload(new() { ["x"] = 0 }));

        Assert.Equal(2, Convert.ToInt32(result.Get("x")));
        Assert.Equal(new[] { "CupPipe.Tests.PipelineTests.AddOneFilter", "CupPipe.Tests.PipelineTests.BoomTap", "CupPipe.Tests.PipelineTests.AddOneFilter#2" }, sp.State.Executed);
        Assert.Equal(new[] { "CupPipe.Tests.PipelineTests.BoomTap" }, sp.State.Errors.Select(e => e.Name));
    }

    // ── Timing ──────────────────────────────────────────────────────

    [Fact]
    public void Observe_RecordsTiming()
    {
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .Observe(timing: true);
        sp.Run(new Payload(new() { ["x"] = 0 }));
        Assert.True(sp.State.Timings.ContainsKey("CupPipe.Tests.PipelineTests.AddOneFilter"));
        Assert.True(sp.State.Timings["CupPipe.Tests.PipelineTests.AddOneFilter"] > 0);
    }

    // ── Contracts ───────────────────────────────────────────────────

    [Fact]
    public void RequireInput_Pass()
    {
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .RequireInput("x");
        var result = sp.Run(new Payload(new() { ["x"] = 1 }));
        Assert.Equal(2, result.Get<int>("x"));
    }

    [Fact]
    public void RequireInput_Fail()
    {
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .RequireInput("missing_key");
        Assert.Throws<ContractViolation>(() =>
            sp.Run(new Payload(new() { ["x"] = 1 })));
    }

    [Fact]
    public void GuaranteeOutput_Pass()
    {
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .GuaranteeOutput("x");
        var result = sp.Run(new Payload(new() { ["x"] = 0 }));
        Assert.Equal(1, result.Get<int>("x"));
    }

    [Fact]
    public void GuaranteeOutput_Fail()
    {
        var sp = new Pipeline()
            .AddFilter(new AddOneFilter())
            .GuaranteeOutput("nonexistent");
        Assert.Throws<ContractViolation>(() =>
            sp.Run(new Payload(new() { ["x"] = 0 })));
    }

    // ── Fluent API ──────────────────────────────────────────────────

    [Fact]
    public void FluentApi_Chains()
    {
        var result = new Pipeline()
            .AddFilter(new AddOneFilter())
            .AddFilter(new AddOneFilter())
            .Observe()
            .RequireInput("x")
            .GuaranteeOutput("x")
            .Run(new Payload(new() { ["x"] = 0 }));

        Assert.Equal(2, result.Get<int>("x"));
    }
}
