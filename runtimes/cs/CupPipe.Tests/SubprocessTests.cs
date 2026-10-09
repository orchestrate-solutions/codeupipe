namespace CupPipe.Tests;

/// <summary>
/// Tests for PersistentSubprocess calling existing polyglot runners.
/// Requires runners to be built (Python always available via python3).
/// </summary>
public class SubprocessTests
{
    private static string PyRunner => Path.GetFullPath(
        Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "py", "runner.py"));

    [Fact]
    public void Python_JsonRoundtrip()
    {
        using var ps = new PersistentSubprocess("python3", PyRunner);
        var result = ps.Call(new Payload(new() { ["greeting"] = "hello" }));
        Assert.Equal("hello", result.Get<string>("greeting"));
        Assert.Equal("python", result.Get<string>("lang"));
    }

    [Fact]
    public void Python_MultipleSequentialCalls()
    {
        using var ps = new PersistentSubprocess("python3", PyRunner);
        for (int i = 0; i < 5; i++)
        {
            var result = ps.Call(new Payload(new() { ["i"] = i }));
            Assert.Equal(i, result.Get<int>("i"));
        }
    }

    [Fact]
    public void Python_TraceIdPreserved()
    {
        using var ps = new PersistentSubprocess("python3", PyRunner);
        var p = new Payload(new() { ["a"] = 1 }, traceId: "trace-cs-001");
        var result = ps.Call(p);
        Assert.Equal("trace-cs-001", result.TraceId);
    }

    [Fact]
    public void Python_MsgpackFormat()
    {
        using var ps = new PersistentSubprocess("python3", PyRunner, fmt: "msgpack");
        var result = ps.Call(new Payload(new() { ["fmt"] = "msgpack" }));
        Assert.Equal("msgpack", result.Get<string>("fmt"));
        Assert.Equal("python", result.Get<string>("lang"));
    }

    [Fact]
    public void Python_InSyncPipeline()
    {
        using var ps = new PersistentSubprocess("python3", PyRunner);
        var pipeline = new Pipeline()
            .AddFilter(new AddMarkerFilter("pre_processed"))
            .AddFilter(ps)
            .AddFilter(new AddMarkerFilter("post_processed"));

        var result = pipeline.Run(new Payload(new() { ["x"] = 42 }));
        Assert.Equal(42, result.Get<int>("x"));
        Assert.Equal(true, result.Get<bool>("pre_processed"));
        Assert.Equal(true, result.Get<bool>("post_processed"));
        Assert.Equal("python", result.Get<string>("lang"));
    }

    // ── Helper filter ───────────────────────────────────────────────

    private class AddMarkerFilter : IFilter
    {
        private readonly string _key;
        public AddMarkerFilter(string key) => _key = key;
        public Payload Call(Payload payload) => payload.Insert(_key, true);
    }
}
