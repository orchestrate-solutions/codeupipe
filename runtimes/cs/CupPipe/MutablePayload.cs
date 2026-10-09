namespace CupPipe;

/// <summary>
/// The explicit mutable escape hatch: <c>Set</c> and <c>Remove</c> change this
/// object in place (where <see cref="Payload.Insert"/> returns a new one).
/// </summary>
public sealed class MutablePayload
{
    private readonly Dictionary<string, object?> _data;
    private readonly string? _traceId;
    private readonly IReadOnlyList<string> _lineage;

    internal MutablePayload(Dictionary<string, object?> data, string? traceId, IReadOnlyList<string> lineage)
    {
        _data = new Dictionary<string, object?>(data);
        _traceId = traceId;
        _lineage = lineage;
    }

    public object? Get(string key, object? defaultValue = null)
        => _data.TryGetValue(key, out var v) ? v : defaultValue;

    public bool Has(string key) => _data.ContainsKey(key);

    public void Set(string key, object? value) => _data[key] = value;

    public void Remove(string key) => _data.Remove(key);

    public Payload ToImmutable() => new(_data, _traceId, _lineage);
}
