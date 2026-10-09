// C# conformance runner: executes cases, reports what happened.
//
//   dotnet run --project conformance/runners/cs < cases.json > results.json
//
// Mirrors conformance/runners/python/runner.py; conformance/run.py judges.
// Uses only the API contract's operations (conformance/API.md).
using System.Text.Json;
using System.Text.Json.Nodes;
using CupPipe;

var taps = new List<object?>();
var hooks = new List<string>();

object? Plain(JsonNode? n) => n switch
{
    null => null,
    JsonObject o => o.ToDictionary(kv => kv.Key, kv => Plain(kv.Value)),
    JsonArray a => a.Select(Plain).ToList(),
    JsonValue v when v.TryGetValue(out bool b) => b,
    JsonValue v when v.TryGetValue(out long l) => l,
    JsonValue v when v.TryGetValue(out double d) => d,
    JsonValue v when v.TryGetValue(out string? s) => s,
    _ => n.ToJsonString(),
};

// Steps are named classes, one per operation: a step is identified by its
// type (conformance/API.md, "Step identity"). A generic wrapper around a
// lambda would give every step the same identity.
IFilter FilterFor(JsonObject s) => (string?)s["op"] switch
{
    "set" => new SetOp((string)s["key"]!, Plain(s["value"])),
    "copy" => new CopyOp((string)s["from"]!, (string)s["to"]!),
    "add" => new AddOp((string)s["key"]!, Plain(s["by"])),
    "append" => new AppendOp((string)s["key"]!, Plain(s["value"])),
    "remove" => new RemoveOp((string)s["key"]!),
    "merge" => new MergeOp((Dictionary<string, object?>)Plain(s["value"])!),
    "has" => new HasOp((string)s["key"]!, (string)s["to"]!),
    "mutate" => new MutateOp((string)s["key"]!, Plain(s["value"])),
    "fail" => new FailOp((string)s["message"]!),
    var op => throw new NotSupportedException($"unknown filter op {op}"),
};

ITap TapFor(JsonObject s) => (string?)s["op"] switch
{
    "record" => new RecordTap(taps, (string)s["key"]!),
    "fail" => new FailTap((string)s["message"]!),
    "noop" => new NoopTap(),
    var op => throw new NotSupportedException($"unknown tap op {op}"),
};

// Predicates are objects (conformance/API.md, "Valve"): IPredicate classes,
// the case's condition on the instance.
IPredicate WhenFor(JsonObject when) => (string?)when["op"] switch
{
    "equals" => new EqualsWhen((string)when["key"]!, when["value"]),
    "truthy" => new TruthyWhen((string)when["key"]!),
    var op => throw new NotSupportedException($"unknown valve op {op}"),
};

Pipeline Build(JsonArray steps) => AddSteps(new Pipeline(), steps);

// A nested case pipeline, as the runner's named pipeline type.
Nested BuildNested(JsonArray steps) => AddSteps(new Nested(), steps);

T AddSteps<T>(T p, JsonArray steps) where T : Pipeline
{
    foreach (var raw in steps)
    {
        var s = raw!.AsObject();
        switch ((string?)s["kind"])
        {
            case "filter": p.AddFilter(FilterFor(s)); break;
            case "tap": p.AddTap(TapFor(s)); break;
            case "valve": p.AddFilter(new Valve(FilterFor(s["filter"]!.AsObject()), WhenFor(s["when"]!.AsObject()))); break;
            case "pipeline": p.AddPipeline(BuildNested(s["steps"]!.AsArray())); break;
            default: throw new NotSupportedException($"unknown step kind {s["kind"]}");
        }
    }
    return p;
}

var cases = JsonNode.Parse(Console.In.ReadToEnd())!.AsArray();
var results = new JsonArray();

if (args.Length > 0 && args[0] == "bench")
{
    // Best of 5 x 20,000 runs after 20,000 warmup runs, in µs per run.
    const int warmup = 20000, runs = 20000, repeats = 5;
    foreach (var raw in cases)
    {
        var c = raw!.AsObject();
        var p = Build(c["steps"]!.AsArray());
        if ((string?)(c["hooks"] as JsonValue) == "noop") p.UseHook(new NoopHook());
        var input = (Dictionary<string, object?>)Plain(c["input"] ?? new JsonObject())!;
        var output = p.Run(new Payload(input)).ToDict();
        for (var i = 0; i < warmup; i++) p.Run(new Payload(input));
        var best = long.MaxValue;
        for (var r = 0; r < repeats; r++)
        {
            var t0 = System.Diagnostics.Stopwatch.GetTimestamp();
            for (var i = 0; i < runs; i++) p.Run(new Payload(input));
            best = Math.Min(best, System.Diagnostics.Stopwatch.GetTimestamp() - t0);
        }
        var us = best * 1_000_000.0 / System.Diagnostics.Stopwatch.Frequency / runs;
        results.Add(JsonSerializer.SerializeToNode(new Dictionary<string, object?>
            { ["id"] = (string)c["id"]!, ["us_per_run"] = us, ["output"] = output }));
    }
    Console.Out.Write(results.ToJsonString());
    return;
}

foreach (var raw in cases)
{
    var c = raw!.AsObject();
    taps.Clear();
    hooks.Clear();
    var id = (string)c["id"]!;
    Pipeline p;
    try { p = Build(c["steps"]!.AsArray()); }
    catch (NotSupportedException e)
    {
        results.Add(new JsonObject { ["id"] = id, ["unsupported"] = e.Message });
        continue;
    }
    var withHooks = c["hooks"] is JsonValue hv && hv.TryGetValue(out bool hb) && hb;
    if (withHooks) p.UseHook(new RecordHook(hooks));
    var input = (Dictionary<string, object?>)Plain(c["input"] ?? new JsonObject())!;
    var result = new Dictionary<string, object?> { ["id"] = id };
    try { result["output"] = p.Run(new Payload(input)).ToDict(); }
    catch (Exception e) { result["error"] = $"{e.GetType().Name}: {e.Message}"; }
    // Steps are identified by their type (conformance/API.md); the cases name
    // them. Each case step adds one pipeline step, in order: map identities
    // back. An identity this map does not know stays as is and fails.
    var caseSteps = c["steps"]!.AsArray();
    var label = p.Identities.Select((ident, i) => (ident, i))
        .ToDictionary(t => t.ident, t => (string)caseSteps[t.i]!["name"]!);
    List<string> Named(IEnumerable<string> ids) => ids.Select(x => label.GetValueOrDefault(x, x)).ToList();
    var state = p.State;
    result["state"] = new Dictionary<string, object?>
    {
        ["executed"] = Named(state.Executed),
        ["skipped"] = Named(state.Skipped),
        ["errors"] = Named(state.Errors.Select(e => e.Name)),
    };
    if (withHooks)
        result["hooks"] = hooks.Select(h =>
        {
            var at = h.IndexOf(':');
            var ident = h[(at + 1)..];
            return h[..(at + 1)] + label.GetValueOrDefault(ident, ident);
        }).ToList();
    result["taps"] = taps.ToList();
    result["input_after"] = input;
    results.Add(JsonSerializer.SerializeToNode(result));
}
Console.Out.Write(results.ToJsonString());

static class Ops
{
    public static object Plus(object? a, object? b) =>
        a is long x && b is long y ? x + y : Convert.ToDouble(a) + Convert.ToDouble(b);

    public static bool Truthy(object? v) => v switch
    {
        null => false,
        bool b => b,
        long l => l != 0,
        double d => d != 0,
        string str => str.Length > 0,
        System.Collections.ICollection c => c.Count > 0,
        _ => true,
    };
}

sealed class SetOp(string key, object? value) : IFilter { public Payload Call(Payload p) => p.Insert(key, value); }
sealed class CopyOp(string from, string to) : IFilter { public Payload Call(Payload p) => p.Insert(to, p.Get(from)); }
sealed class AddOp(string key, object? by) : IFilter
{
    public Payload Call(Payload p) => p.Insert(key, Ops.Plus(p.Get(key, 0L), by));
}
sealed class AppendOp(string key, object? value) : IFilter
{
    public Payload Call(Payload p)
    {
        var next = p.Get(key) is List<object?> cur ? new List<object?>(cur) : new List<object?>();
        next.Add(value);
        return p.Insert(key, next);
    }
}
sealed class RemoveOp(string key) : IFilter { public Payload Call(Payload p) => p.Remove(key); }
sealed class MergeOp(Dictionary<string, object?> value) : IFilter { public Payload Call(Payload p) => p.Merge(new Payload(value)); }
sealed class HasOp(string key, string to) : IFilter { public Payload Call(Payload p) => p.Insert(to, p.Has(key)); }
sealed class MutateOp(string key, object? value) : IFilter
{
    public Payload Call(Payload p)
    {
        var m = p.WithMutation();
        m.Set(key, value);
        return m.ToImmutable();
    }
}
sealed class FailOp(string message) : IFilter { public Payload Call(Payload p) => throw new InvalidOperationException(message); }
sealed class RecordTap(List<object?> taps, string key) : ITap { public void Observe(Payload p) => taps.Add(p.Get(key)); }
sealed class FailTap(string message) : ITap { public void Observe(Payload p) => throw new InvalidOperationException(message); }
sealed class NoopTap : ITap { public void Observe(Payload p) { } }
sealed class EqualsWhen(string key, JsonNode? value) : IPredicate
{
    public bool Test(Payload p) => JsonNode.DeepEquals(JsonSerializer.SerializeToNode(p.Get(key)), value);
}
sealed class TruthyWhen(string key) : IPredicate { public bool Test(Payload p) => Ops.Truthy(p.Get(key)); }
/// <summary>The runner's named pipeline type: only named Pipeline subclasses nest.</summary>
sealed class Nested : Pipeline { }

sealed class NoopHook : Hook { }

sealed class RecordHook(List<string> log) : Hook
{
    public override void Before(string? step, Payload p) => log.Add("before:" + step);
    public override void After(string? step, Payload p) => log.Add("after:" + step);
    public override void OnError(string? step, Exception e, Payload p) => log.Add("error:" + step);
}
