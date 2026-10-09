using System.Diagnostics.Contracts;
using System.Text.Json;

namespace CupPipe;

/// <summary>
/// Immutable data container — carries data through the pipeline.
/// Returns fresh copies on modification for safety.
/// See also: TypeScript, Python, Rust, Go implementations.
/// </summary>
public sealed class Payload
{
    private readonly Dictionary<string, object?> _data;

    public string? TraceId { get; }
    public IReadOnlyList<string> Lineage { get; }

    public Payload(
        Dictionary<string, object?>? data = null,
        string? traceId = null,
        IReadOnlyList<string>? lineage = null)
    {
        _data = data != null ? new Dictionary<string, object?>(data) : new();
        TraceId = traceId;
        Lineage = lineage ?? Array.Empty<string>();
    }

    /// <summary>Return the value for key, or default if absent.</summary>
    public object? Get(string key, object? defaultValue = null)
        => _data.TryGetValue(key, out var v) ? v : defaultValue;

    /// <summary>Typed get — returns T or default.</summary>
    public T? Get<T>(string key, T? defaultValue = default)
    {
        if (!_data.TryGetValue(key, out var raw))
            return defaultValue;

        if (raw is T typed)
            return typed;

        // Handle JsonElement from deserialization
        if (raw is JsonElement el)
            return ConvertJsonElement<T>(el, defaultValue);

        // A present value of the wrong type fails loudly (API contract): it
        // must not be mistaken for a missing key.
        return (T?)Convert.ChangeType(raw, typeof(T));
    }

    /// <summary>Whether the key is present (even with a null value).</summary>
    public bool Has(string key) => _data.ContainsKey(key);

    /// <summary>Return a fresh Payload without the key.</summary>
    [Pure]
    public Payload Remove(string key)
    {
        var copy = new Dictionary<string, object?>(_data);
        copy.Remove(key);
        return new Payload(copy, TraceId, Lineage);
    }

    /// <summary>A mutable copy; see <see cref="MutablePayload"/>.</summary>
    public MutablePayload WithMutation() => new(_data, TraceId, Lineage);

    /// <summary>Return a fresh Payload with the addition.</summary>
    [Pure]
    public Payload Insert(string key, object? value)
    {
        var copy = new Dictionary<string, object?>(_data) { [key] = value };
        return new Payload(copy, TraceId, Lineage);
    }

    /// <summary>Combine payloads, other takes precedence on conflicts.</summary>
    [Pure]
    public Payload Merge(Payload other)
    {
        var copy = new Dictionary<string, object?>(_data);
        foreach (var kv in other._data)
            copy[kv.Key] = kv.Value;
        var trace = TraceId ?? other.TraceId;
        var lineage = Lineage.Concat(other.Lineage).ToList();
        return new Payload(copy, trace, lineage);
    }

    /// <summary>Return a new Payload with trace ID set.</summary>
    [Pure]
    public Payload WithTrace(string traceId)
        => new(_data, traceId, Lineage);

    /// <summary>Record a processing step in lineage.</summary>
    internal Payload Stamp(string stepName)
    {
        var newLineage = Lineage.Concat(new[] { stepName }).ToList();
        // Share _data dict — no copy (immutable contract)
        return new Payload(newLineage, _data, TraceId);
    }

    // Internal constructor that shares dict reference (no copy)
    private Payload(List<string> lineage, Dictionary<string, object?> sharedData, string? traceId)
    {
        _data = sharedData; // share, not copy
        TraceId = traceId;
        Lineage = lineage;
    }

    /// <summary>Express as dictionary for ecosystem integration.</summary>
    public Dictionary<string, object?> ToDict()
        => new(_data);

    public override string ToString()
        => TraceId != null
            ? $"Payload({JsonSerializer.Serialize(_data)}, traceId='{TraceId}')"
            : $"Payload({JsonSerializer.Serialize(_data)})";

    // ── JSON element helpers ────────────────────────────────────────

    private static T? ConvertJsonElement<T>(JsonElement el, T? fallback)
    {
        return el.ValueKind switch
        {
            JsonValueKind.String when typeof(T) == typeof(string)
                => (T)(object)el.GetString()!,
            JsonValueKind.Number when typeof(T) == typeof(int)
                => (T)(object)el.GetInt32(),
            JsonValueKind.Number when typeof(T) == typeof(long)
                => (T)(object)el.GetInt64(),
            JsonValueKind.Number when typeof(T) == typeof(double)
                => (T)(object)el.GetDouble(),
            JsonValueKind.Number when typeof(T) == typeof(float)
                => (T)(object)(float)el.GetDouble(),
            JsonValueKind.True or JsonValueKind.False when typeof(T) == typeof(bool)
                => (T)(object)el.GetBoolean(),
            _ => throw new InvalidCastException(
                $"cannot read a JSON {el.ValueKind} as {typeof(T).Name}")
        };
    }
}
