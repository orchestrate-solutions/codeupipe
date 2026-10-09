namespace CupPipe.Tests;

/// <summary>Tests for WireFormat: JSON + msgpack serialize/deserialize, auto-detection.</summary>
public class WireFormatTests
{
    [Fact]
    public void Json_Roundtrip()
    {
        var p = new Payload(new() { ["name"] = "Alice", ["age"] = 30 }, traceId: "t-001");
        var bytes = WireFormat.Serialize(p, "json");
        var p2 = WireFormat.Deserialize(bytes, "json");

        Assert.Equal("Alice", p2.Get<string>("name"));
        Assert.Equal(30, p2.Get<int>("age"));
        Assert.Equal("t-001", p2.TraceId);
    }

    [Fact]
    public void Json_AutoDetect()
    {
        var p = new Payload(new() { ["x"] = 1 });
        var bytes = WireFormat.Serialize(p, "json");
        // Auto-detect should pick JSON from first byte '{'
        var p2 = WireFormat.Deserialize(bytes);
        Assert.Equal(1, p2.Get<int>("x"));
    }

    [Fact]
    public void Msgpack_Roundtrip()
    {
        var p = new Payload(new() { ["name"] = "Bob", ["score"] = 99 }, traceId: "t-002");
        var bytes = WireFormat.Serialize(p, "msgpack");
        var p2 = WireFormat.Deserialize(bytes, "msgpack");

        Assert.Equal("Bob", p2.Get<string>("name"));
        Assert.Equal(99, p2.Get<int>("score"));
        Assert.Equal("t-002", p2.TraceId);
    }

    [Fact]
    public void Msgpack_AutoDetect()
    {
        var p = new Payload(new() { ["x"] = 42 });
        var bytes = WireFormat.Serialize(p, "msgpack");
        // Auto-detect from first byte (0x80-0x8f for fixmap)
        var p2 = WireFormat.Deserialize(bytes);
        Assert.Equal(42, p2.Get<int>("x"));
    }

    [Fact]
    public void Lineage_Preserved_Json()
    {
        var p = new Payload(
            new() { ["x"] = 1 },
            lineage: new List<string> { "step1", "step2" }
        );
        var bytes = WireFormat.Serialize(p, "json");
        var p2 = WireFormat.Deserialize(bytes, "json");
        Assert.Equal(new[] { "step1", "step2" }, p2.Lineage);
    }

    [Fact]
    public void Lineage_Preserved_Msgpack()
    {
        var p = new Payload(
            new() { ["x"] = 1 },
            lineage: new List<string> { "a", "b", "c" }
        );
        var bytes = WireFormat.Serialize(p, "msgpack");
        var p2 = WireFormat.Deserialize(bytes, "msgpack");
        Assert.Equal(new[] { "a", "b", "c" }, p2.Lineage);
    }

    [Fact]
    public void Msgpack_HandlesNested()
    {
        var nested = new Dictionary<string, object?>
        {
            ["inner"] = new Dictionary<string, object?> { ["deep"] = "value" }
        };
        var p = new Payload(nested);
        var bytes = WireFormat.Serialize(p, "msgpack");
        var p2 = WireFormat.Deserialize(bytes, "msgpack");
        var inner = p2.Get("inner") as Dictionary<string, object?>;
        Assert.NotNull(inner);
        Assert.Equal("value", inner!["deep"]);
    }

    [Fact]
    public void Msgpack_HandlesBooleans()
    {
        var p = new Payload(new() { ["flag"] = true, ["off"] = false });
        var bytes = WireFormat.Serialize(p, "msgpack");
        var p2 = WireFormat.Deserialize(bytes, "msgpack");
        Assert.Equal(true, p2.Get<bool>("flag"));
        Assert.Equal(false, p2.Get<bool>("off"));
    }

    [Fact]
    public void Msgpack_HandlesNegativeInts()
    {
        var p = new Payload(new() { ["neg"] = -5, ["big_neg"] = -1000 });
        var bytes = WireFormat.Serialize(p, "msgpack");
        var p2 = WireFormat.Deserialize(bytes, "msgpack");
        Assert.Equal(-5, p2.Get<int>("neg"));
        Assert.Equal(-1000, p2.Get<int>("big_neg"));
    }

    [Fact]
    public void Msgpack_HandlesFloats()
    {
        var p = new Payload(new() { ["pi"] = 3.14159 });
        var bytes = WireFormat.Serialize(p, "msgpack");
        var p2 = WireFormat.Deserialize(bytes, "msgpack");
        Assert.Equal(3.14159, p2.Get<double>("pi"), 4);
    }

    [Fact]
    public void UnsupportedFormat_Throws()
    {
        var p = new Payload(new() { ["x"] = 1 });
        Assert.Throws<ArgumentException>(() => WireFormat.Serialize(p, "xml"));
    }

    [Fact]
    public void EmptyData_Throws()
    {
        Assert.Throws<ArgumentException>(() => WireFormat.Deserialize(Array.Empty<byte>()));
    }

    [Fact]
    public void IsMsgpackMap_Correct()
    {
        Assert.True(WireFormat.IsMsgpackMap(0x80));
        Assert.True(WireFormat.IsMsgpackMap(0x8F));
        Assert.True(WireFormat.IsMsgpackMap(0xDE));
        Assert.True(WireFormat.IsMsgpackMap(0xDF));
        Assert.False(WireFormat.IsMsgpackMap(0x7B)); // '{'
        Assert.False(WireFormat.IsMsgpackMap(0x00)); // shm sentinel
    }
}
