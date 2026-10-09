using System.Text;
using System.Text.Json;

namespace CupPipe;

/// <summary>
/// Wire format serialization/deserialization for the CUP protocol.
/// Supports JSON and msgpack. Auto-detects format from first byte.
///
/// Protocol: [4-byte LE length][payload bytes]
/// First byte detection:
///   0x7b '{' → JSON
///   0x80-0x8f / 0xde / 0xdf → msgpack map
///   0x00 → shm file handle
/// </summary>
public static class WireFormat
{
    /// <summary>Serialize a Payload to wire bytes in the given format.</summary>
    public static byte[] Serialize(Payload payload, string fmt = "json")
    {
        var envelope = new Dictionary<string, object?> { ["data"] = payload.ToDict() };
        if (payload.TraceId != null)
            envelope["trace_id"] = payload.TraceId;
        if (payload.Lineage.Count > 0)
            envelope["lineage"] = payload.Lineage.ToList();

        return fmt switch
        {
            "json" => JsonSerializer.SerializeToUtf8Bytes(envelope),
            "msgpack" => SerializeMsgpack(envelope),
            _ => throw new ArgumentException($"Unsupported format: {fmt}")
        };
    }

    /// <summary>Deserialize wire bytes to a Payload. Auto-detects format.</summary>
    public static Payload Deserialize(byte[] data)
    {
        if (data.Length == 0)
            throw new ArgumentException("Empty data");

        byte first = data[0];
        if (first == 0x7B) // '{'
            return DeserializeJson(data);
        if (IsMsgpackMap(first))
            return DeserializeMsgpack(data);

        throw new ArgumentException($"Unknown wire format, first byte: 0x{first:X2}");
    }

    /// <summary>Deserialize with explicit format.</summary>
    public static Payload Deserialize(byte[] data, string fmt)
    {
        return fmt switch
        {
            "json" => DeserializeJson(data),
            "msgpack" => DeserializeMsgpack(data),
            _ => throw new ArgumentException($"Unsupported format: {fmt}")
        };
    }

    /// <summary>Detect if the first byte indicates a msgpack map.</summary>
    public static bool IsMsgpackMap(byte b)
        => (b >= 0x80 && b <= 0x8F) || b == 0xDE || b == 0xDF;

    // ── JSON ────────────────────────────────────────────────────────

    private static Payload DeserializeJson(byte[] data)
    {
        var doc = JsonDocument.Parse(data);
        var root = doc.RootElement;

        var dict = new Dictionary<string, object?>();
        if (root.TryGetProperty("data", out var dataEl) && dataEl.ValueKind == JsonValueKind.Object)
        {
            foreach (var prop in dataEl.EnumerateObject())
                dict[prop.Name] = JsonElementToObject(prop.Value);
        }

        string? traceId = null;
        if (root.TryGetProperty("trace_id", out var traceEl) && traceEl.ValueKind == JsonValueKind.String)
            traceId = traceEl.GetString();

        List<string>? lineage = null;
        if (root.TryGetProperty("lineage", out var linEl) && linEl.ValueKind == JsonValueKind.Array)
        {
            lineage = new List<string>();
            foreach (var item in linEl.EnumerateArray())
                if (item.ValueKind == JsonValueKind.String)
                    lineage.Add(item.GetString()!);
        }

        return new Payload(dict, traceId, lineage);
    }

    private static object? JsonElementToObject(JsonElement el)
    {
        return el.ValueKind switch
        {
            JsonValueKind.String => el.GetString(),
            JsonValueKind.Number when el.TryGetInt32(out var i) => i,
            JsonValueKind.Number when el.TryGetInt64(out var l) => l,
            JsonValueKind.Number => el.GetDouble(),
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            JsonValueKind.Null => null,
            JsonValueKind.Array => el.EnumerateArray().Select(JsonElementToObject).ToList(),
            JsonValueKind.Object => el.EnumerateObject()
                .ToDictionary(p => p.Name, p => JsonElementToObject(p.Value)),
            _ => el.GetRawText()
        };
    }

    // ── msgpack ─────────────────────────────────────────────────────

    private static byte[] SerializeMsgpack(Dictionary<string, object?> envelope)
    {
        using var ms = new MemoryStream();
        MsgpackWriter.WriteMap(ms, envelope);
        return ms.ToArray();
    }

    private static Payload DeserializeMsgpack(byte[] data)
    {
        int offset = 0;
        var envelope = MsgpackReader.ReadObject(data, ref offset) as Dictionary<string, object?>;
        if (envelope == null)
            throw new InvalidOperationException("Expected msgpack map at root");

        var dict = new Dictionary<string, object?>();
        if (envelope.TryGetValue("data", out var dataObj) && dataObj is Dictionary<string, object?> dataDict)
            dict = dataDict;

        string? traceId = envelope.TryGetValue("trace_id", out var t) ? t?.ToString() : null;

        List<string>? lineage = null;
        if (envelope.TryGetValue("lineage", out var linObj) && linObj is List<object?> linList)
            lineage = linList.Where(x => x != null).Select(x => x!.ToString()!).ToList();

        return new Payload(dict, traceId, lineage);
    }
}

// ── Minimal msgpack reader (subset: maps, arrays, strings, ints, bools, nil, bin) ──

public static class MsgpackReader
{
    public static object? ReadObject(byte[] data, ref int offset)
    {
        if (offset >= data.Length) return null;
        byte b = data[offset];

        // fixmap 0x80-0x8f
        if (b >= 0x80 && b <= 0x8F)
        {
            int count = b & 0x0F;
            offset++;
            return ReadMapEntries(data, ref offset, count);
        }
        // map16 0xde
        if (b == 0xDE)
        {
            offset++;
            int count = ReadUInt16BE(data, ref offset);
            return ReadMapEntries(data, ref offset, count);
        }
        // map32 0xdf
        if (b == 0xDF)
        {
            offset++;
            int count = (int)ReadUInt32BE(data, ref offset);
            return ReadMapEntries(data, ref offset, count);
        }
        // fixstr 0xa0-0xbf
        if (b >= 0xA0 && b <= 0xBF)
        {
            int len = b & 0x1F;
            offset++;
            var s = Encoding.UTF8.GetString(data, offset, len);
            offset += len;
            return s;
        }
        // str8 0xd9
        if (b == 0xD9)
        {
            offset++;
            int len = data[offset++];
            var s = Encoding.UTF8.GetString(data, offset, len);
            offset += len;
            return s;
        }
        // str16 0xda
        if (b == 0xDA)
        {
            offset++;
            int len = ReadUInt16BE(data, ref offset);
            var s = Encoding.UTF8.GetString(data, offset, len);
            offset += len;
            return s;
        }
        // str32 0xdb
        if (b == 0xDB)
        {
            offset++;
            int len = (int)ReadUInt32BE(data, ref offset);
            var s = Encoding.UTF8.GetString(data, offset, len);
            offset += len;
            return s;
        }
        // fixarray 0x90-0x9f
        if (b >= 0x90 && b <= 0x9F)
        {
            int count = b & 0x0F;
            offset++;
            return ReadArrayEntries(data, ref offset, count);
        }
        // array16 0xdc
        if (b == 0xDC)
        {
            offset++;
            int count = ReadUInt16BE(data, ref offset);
            return ReadArrayEntries(data, ref offset, count);
        }
        // array32 0xdd
        if (b == 0xDD)
        {
            offset++;
            int count = (int)ReadUInt32BE(data, ref offset);
            return ReadArrayEntries(data, ref offset, count);
        }
        // positive fixint 0x00-0x7f
        if (b <= 0x7F)
        {
            offset++;
            return (int)b;
        }
        // negative fixint 0xe0-0xff
        if (b >= 0xE0)
        {
            offset++;
            return (int)(sbyte)b;
        }
        // uint8 0xcc
        if (b == 0xCC) { offset++; return (int)data[offset++]; }
        // uint16 0xcd
        if (b == 0xCD) { offset++; return (int)ReadUInt16BE(data, ref offset); }
        // uint32 0xce
        if (b == 0xCE) { offset++; return (int)ReadUInt32BE(data, ref offset); }
        // uint64 0xcf
        if (b == 0xCF)
        {
            offset++;
            long val = ((long)ReadUInt32BE(data, ref offset) << 32) | ReadUInt32BE(data, ref offset);
            return val;
        }
        // int8 0xd0
        if (b == 0xD0) { offset++; return (int)(sbyte)data[offset++]; }
        // int16 0xd1
        if (b == 0xD1) { offset++; return (int)(short)ReadUInt16BE(data, ref offset); }
        // int32 0xd2
        if (b == 0xD2) { offset++; return (int)ReadUInt32BE(data, ref offset); }
        // int64 0xd3
        if (b == 0xD3)
        {
            offset++;
            long val = ((long)ReadUInt32BE(data, ref offset) << 32) | ReadUInt32BE(data, ref offset);
            return val;
        }
        // float32 0xca
        if (b == 0xCA)
        {
            offset++;
            var bytes = new byte[4];
            Array.Copy(data, offset, bytes, 0, 4);
            if (BitConverter.IsLittleEndian) Array.Reverse(bytes);
            offset += 4;
            return (double)BitConverter.ToSingle(bytes);
        }
        // float64 0xcb
        if (b == 0xCB)
        {
            offset++;
            var bytes = new byte[8];
            Array.Copy(data, offset, bytes, 0, 8);
            if (BitConverter.IsLittleEndian) Array.Reverse(bytes);
            offset += 8;
            return BitConverter.ToDouble(bytes);
        }
        // nil 0xc0
        if (b == 0xC0) { offset++; return null; }
        // false 0xc2
        if (b == 0xC2) { offset++; return false; }
        // true 0xc3
        if (b == 0xC3) { offset++; return true; }
        // bin8 0xc4
        if (b == 0xC4)
        {
            offset++;
            int len = data[offset++];
            var bin = new byte[len];
            Array.Copy(data, offset, bin, 0, len);
            offset += len;
            return bin;
        }
        // bin16 0xc5
        if (b == 0xC5)
        {
            offset++;
            int len = ReadUInt16BE(data, ref offset);
            var bin = new byte[len];
            Array.Copy(data, offset, bin, 0, len);
            offset += len;
            return bin;
        }

        throw new InvalidOperationException($"Unsupported msgpack byte: 0x{b:X2} at offset {offset}");
    }

    private static Dictionary<string, object?> ReadMapEntries(byte[] data, ref int offset, int count)
    {
        var map = new Dictionary<string, object?>(count);
        for (int i = 0; i < count; i++)
        {
            var key = ReadObject(data, ref offset)?.ToString() ?? "";
            var val = ReadObject(data, ref offset);
            map[key] = val;
        }
        return map;
    }

    private static List<object?> ReadArrayEntries(byte[] data, ref int offset, int count)
    {
        var list = new List<object?>(count);
        for (int i = 0; i < count; i++)
            list.Add(ReadObject(data, ref offset));
        return list;
    }

    private static ushort ReadUInt16BE(byte[] data, ref int offset)
    {
        ushort v = (ushort)((data[offset] << 8) | data[offset + 1]);
        offset += 2;
        return v;
    }

    private static uint ReadUInt32BE(byte[] data, ref int offset)
    {
        uint v = ((uint)data[offset] << 24) | ((uint)data[offset + 1] << 16)
               | ((uint)data[offset + 2] << 8) | data[offset + 3];
        offset += 4;
        return v;
    }
}

// ── Minimal msgpack writer ──────────────────────────────────────────

public static class MsgpackWriter
{
    public static void WriteMap(Stream s, Dictionary<string, object?> map)
    {
        int count = map.Count;
        if (count <= 15)
            s.WriteByte((byte)(0x80 | count));
        else if (count <= 0xFFFF)
        {
            s.WriteByte(0xDE);
            WriteUInt16BE(s, (ushort)count);
        }
        else
        {
            s.WriteByte(0xDF);
            WriteUInt32BE(s, (uint)count);
        }

        foreach (var kv in map)
        {
            WriteObject(s, kv.Key);
            WriteObject(s, kv.Value);
        }
    }

    public static void WriteObject(Stream s, object? value)
    {
        switch (value)
        {
            case null:
                s.WriteByte(0xC0);
                break;
            case bool b:
                s.WriteByte(b ? (byte)0xC3 : (byte)0xC2);
                break;
            case string str:
                WriteString(s, str);
                break;
            case int i:
                WriteInt(s, i);
                break;
            case long l:
                WriteInt(s, l);
                break;
            case double d:
                WriteFloat64(s, d);
                break;
            case float f:
                WriteFloat64(s, f);
                break;
            case Dictionary<string, object?> map:
                WriteMap(s, map);
                break;
            case IList<object?> list:
                WriteArray(s, list);
                break;
            case IReadOnlyList<string> strList:
                WriteArray(s, strList.Cast<object?>().ToList());
                break;
            case IList<string> strList2:
                WriteArray(s, strList2.Cast<object?>().ToList());
                break;
            case byte[] bin:
                WriteBin(s, bin);
                break;
            default:
                // Fallback: write as string
                WriteString(s, value.ToString() ?? "");
                break;
        }
    }

    private static void WriteString(Stream s, string str)
    {
        var bytes = Encoding.UTF8.GetBytes(str);
        if (bytes.Length <= 31)
            s.WriteByte((byte)(0xA0 | bytes.Length));
        else if (bytes.Length <= 0xFF)
        {
            s.WriteByte(0xD9);
            s.WriteByte((byte)bytes.Length);
        }
        else if (bytes.Length <= 0xFFFF)
        {
            s.WriteByte(0xDA);
            WriteUInt16BE(s, (ushort)bytes.Length);
        }
        else
        {
            s.WriteByte(0xDB);
            WriteUInt32BE(s, (uint)bytes.Length);
        }
        s.Write(bytes);
    }

    private static void WriteInt(Stream s, long v)
    {
        if (v >= 0 && v <= 0x7F)
            s.WriteByte((byte)v);
        else if (v >= -32 && v < 0)
            s.WriteByte((byte)(v & 0xFF));
        else if (v >= sbyte.MinValue && v <= sbyte.MaxValue)
        {
            s.WriteByte(0xD0);
            s.WriteByte((byte)(sbyte)v);
        }
        else if (v >= short.MinValue && v <= short.MaxValue)
        {
            s.WriteByte(0xD1);
            WriteUInt16BE(s, (ushort)(short)v);
        }
        else if (v >= int.MinValue && v <= int.MaxValue)
        {
            s.WriteByte(0xD2);
            WriteUInt32BE(s, (uint)(int)v);
        }
        else
        {
            s.WriteByte(0xD3);
            WriteUInt32BE(s, (uint)(v >> 32));
            WriteUInt32BE(s, (uint)(v & 0xFFFFFFFF));
        }
    }

    private static void WriteFloat64(Stream s, double v)
    {
        s.WriteByte(0xCB);
        var bytes = BitConverter.GetBytes(v);
        if (BitConverter.IsLittleEndian) Array.Reverse(bytes);
        s.Write(bytes);
    }

    private static void WriteArray(Stream s, IList<object?> arr)
    {
        if (arr.Count <= 15)
            s.WriteByte((byte)(0x90 | arr.Count));
        else if (arr.Count <= 0xFFFF)
        {
            s.WriteByte(0xDC);
            WriteUInt16BE(s, (ushort)arr.Count);
        }
        else
        {
            s.WriteByte(0xDD);
            WriteUInt32BE(s, (uint)arr.Count);
        }
        foreach (var item in arr)
            WriteObject(s, item);
    }

    private static void WriteBin(Stream s, byte[] bin)
    {
        if (bin.Length <= 0xFF)
        {
            s.WriteByte(0xC4);
            s.WriteByte((byte)bin.Length);
        }
        else if (bin.Length <= 0xFFFF)
        {
            s.WriteByte(0xC5);
            WriteUInt16BE(s, (ushort)bin.Length);
        }
        else
        {
            s.WriteByte(0xC6);
            WriteUInt32BE(s, (uint)bin.Length);
        }
        s.Write(bin);
    }

    private static void WriteUInt16BE(Stream s, ushort v)
    {
        s.WriteByte((byte)(v >> 8));
        s.WriteByte((byte)(v & 0xFF));
    }

    private static void WriteUInt32BE(Stream s, uint v)
    {
        s.WriteByte((byte)(v >> 24));
        s.WriteByte((byte)((v >> 16) & 0xFF));
        s.WriteByte((byte)((v >> 8) & 0xFF));
        s.WriteByte((byte)(v & 0xFF));
    }
}
