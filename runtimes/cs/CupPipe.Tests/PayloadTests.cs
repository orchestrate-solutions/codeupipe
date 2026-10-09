namespace CupPipe.Tests;

/// <summary>RED → GREEN tests for Payload: immutability, get/insert, trace, lineage, merge.</summary>
public class PayloadTests
{
    [Fact]
    public void EmptyPayload_HasNoData()
    {
        var p = new Payload();
        Assert.Null(p.Get("anything"));
        Assert.Null(p.TraceId);
        Assert.Empty(p.Lineage);
    }

    [Fact]
    public void Get_ReturnsValue()
    {
        var p = new Payload(new() { ["x"] = 42 });
        Assert.Equal(42, p.Get("x"));
    }

    [Fact]
    public void Get_ReturnsDefault_WhenMissing()
    {
        var p = new Payload(new() { ["x"] = 1 });
        Assert.Equal("fallback", p.Get("missing", "fallback"));
    }

    [Fact]
    public void GetTyped_ReturnsTypedValue()
    {
        var p = new Payload(new() { ["name"] = "Alice", ["count"] = 5 });
        Assert.Equal("Alice", p.Get<string>("name"));
        Assert.Equal(5, p.Get<int>("count"));
    }

    [Fact]
    public void Insert_ReturnsNewPayload()
    {
        var p1 = new Payload(new() { ["x"] = 1 });
        var p2 = p1.Insert("y", 2);

        // Original unchanged
        Assert.Null(p1.Get("y"));
        // New has both
        Assert.Equal(1, p2.Get("x"));
        Assert.Equal(2, p2.Get("y"));
    }

    [Fact]
    public void Insert_OverwritesKey()
    {
        var p = new Payload(new() { ["x"] = 1 });
        var p2 = p.Insert("x", 99);
        Assert.Equal(1, p.Get("x"));
        Assert.Equal(99, p2.Get("x"));
    }

    [Fact]
    public void TraceId_Preserved()
    {
        var p = new Payload(new() { ["a"] = 1 }, traceId: "t-001");
        Assert.Equal("t-001", p.TraceId);

        var p2 = p.Insert("b", 2);
        Assert.Equal("t-001", p2.TraceId);
    }

    [Fact]
    public void WithTrace_SetsNewTraceId()
    {
        var p = new Payload(new() { ["x"] = 1 });
        var p2 = p.WithTrace("trace-123");
        Assert.Null(p.TraceId);
        Assert.Equal("trace-123", p2.TraceId);
    }

    [Fact]
    public void Merge_CombinesPayloads()
    {
        var a = new Payload(new() { ["x"] = 1, ["shared"] = "a" });
        var b = new Payload(new() { ["y"] = 2, ["shared"] = "b" });
        var merged = a.Merge(b);

        Assert.Equal(1, merged.Get("x"));
        Assert.Equal(2, merged.Get("y"));
        Assert.Equal("b", merged.Get("shared")); // b wins
    }

    [Fact]
    public void ToDict_ReturnsCopy()
    {
        var p = new Payload(new() { ["a"] = 1 });
        var dict = p.ToDict();
        dict["a"] = 999;
        Assert.Equal(1, p.Get("a")); // Original unaffected
    }

    [Fact]
    public void Lineage_Tracked()
    {
        var p = new Payload(new() { ["x"] = 1 });
        var p2 = p.Stamp("step1").Stamp("step2");
        Assert.Equal(new[] { "step1", "step2" }, p2.Lineage);
        Assert.Empty(p.Lineage); // Original unchanged
    }

    [Fact]
    public void ToString_IncludesData()
    {
        var p = new Payload(new() { ["x"] = 1 });
        Assert.Contains("x", p.ToString());
    }
}
