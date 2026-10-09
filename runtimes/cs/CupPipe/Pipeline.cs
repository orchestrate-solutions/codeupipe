using System.Diagnostics;
using System.Runtime.CompilerServices;

namespace CupPipe;

/// <summary>
/// The pipeline. <see cref="Run"/> is synchronous; the runtime has no async
/// steps, so there is no RunAsync (conformance/API.md). Steps have no names:
/// each is identified by its type (conformance/API.md, "Step identity"),
/// which State and Hooks report. Unsealed: nested pipelines are named
/// subclasses.
/// </summary>
public class Pipeline
{
    private readonly Dictionary<string, int> _occurrences = new();
    private readonly Dictionary<string, string> _stepSites = new();

    private readonly List<(string Name, object Step, string Type)> _steps = new();
    private readonly List<Hook> _hooks = new();
    private bool _observeTiming;
    private bool _observeLineage;
    private HashSet<string>? _requireInputKeys;
    private HashSet<string>? _guaranteeOutputKeys;

    /// <summary>What happened in the last run.</summary>
    public State State { get; private set; } = new();

    /// <summary>Each step's identity, in order.</summary>
    public IReadOnlyList<string> Identities => _steps.Select(s => s.Name).ToList();

    /// <summary>identity -> <c>File.cs:line</c> of the Add call (detail, not identity).</summary>
    public IReadOnlyDictionary<string, string> StepSites => _stepSites;

    private string Identity(string baseId, int line, string file)
    {
        var n = _occurrences.GetValueOrDefault(baseId) + 1;
        _occurrences[baseId] = n;
        var id = n == 1 ? baseId : $"{baseId}#{n}";
        _stepSites[id] = $"{Path.GetFileName(file)}:{line}";
        return id;
    }

    // The caller-info parameters come first among the optionals, so a leftover
    // name argument (AddFilter(f, "name")) fails to compile rather than
    // binding to the file path.

    /// <summary>Add a filter or a <see cref="Valve"/>, identified by its type.</summary>
    public Pipeline AddFilter(IFilter filter, [CallerLineNumber] int line = 0, [CallerFilePath] string file = "")
    {
        _steps.Add((Identity(StepIdentity.Identify(filter, "Filter"), line, file), filter, "filter"));
        return this;
    }

    /// <summary>Add a tap, identified by its type.</summary>
    public Pipeline AddTap(ITap tap, [CallerLineNumber] int line = 0, [CallerFilePath] string file = "")
    {
        _steps.Add((Identity(StepIdentity.Identify(tap, "Tap"), line, file), tap, "tap"));
        return this;
    }

    /// <summary>Nest a named Pipeline subclass; it is one step in this pipeline's State.</summary>
    public Pipeline AddPipeline(Pipeline pipeline, [CallerLineNumber] int line = 0, [CallerFilePath] string file = "")
    {
        if (pipeline.GetType() == typeof(Pipeline))
            throw new AnonymousStep(
                "A nested pipeline must be a named Pipeline subclass (class Onboarding : Pipeline), " +
                "identified like a filter. A plain new Pipeline() can only run at the top level.");
        _steps.Add((Identity(StepIdentity.Identify(pipeline, "Nested pipeline"), line, file), pipeline, "pipeline"));
        return this;
    }

    public Pipeline UseHook(Hook hook)
    {
        _hooks.Add(hook);
        return this;
    }

    public Pipeline Observe(bool timing = true, bool lineage = false)
    {
        _observeTiming = timing;
        _observeLineage = lineage;
        return this;
    }

    public Pipeline RequireInput(params string[] keys)
    {
        _requireInputKeys = new HashSet<string>(keys);
        return this;
    }

    public Pipeline GuaranteeOutput(params string[] keys)
    {
        _guaranteeOutputKeys = new HashSet<string>(keys);
        return this;
    }

    /// <summary>Execute the pipeline.</summary>
    public Payload Run(Payload payload)
    {
        State = new State();

        if (_requireInputKeys != null)
        {
            var data = payload.ToDict();
            var missing = _requireInputKeys.Where(k => !data.ContainsKey(k)).ToList();
            if (missing.Count > 0)
                throw new ContractViolation(
                    $"Input contract violated — missing keys: {string.Join(", ", missing.OrderBy(x => x))}");
        }

        // Hook: pipeline start (step = null)
        foreach (var hook in _hooks)
            hook.Before(null, payload);

        string? stepName = null;
        long stepT0 = 0;
        string? failing = null; // the step running when an exception escapes

        try
        {
            foreach (var (name, step, type) in _steps)
            {
                stepName = name;

                if (type == "tap")
                {
                    // Plane B: a Tap failure never halts the pipeline. The
                    // exception is recorded and the run continues; OnError
                    // hooks are not fired (they govern Plane A).
                    try
                    {
                        ((ITap)step).Observe(payload);
                    }
                    catch (Exception tapError)
                    {
                        State.RecordError(name, tapError);
                    }
                    State.MarkExecuted(name);
                    continue;
                }

                stepT0 = Stopwatch.GetTimestamp();
                failing = name;

                foreach (var hook in _hooks)
                    hook.Before(name, payload);

                if (type == "pipeline")
                {
                    payload = ((Pipeline)step).Run(payload);
                    State.MarkExecuted(name);
                }
                else
                {
                    payload = ((IFilter)step).Call(payload);
                    if (step is Valve { LastSkipped: true })
                        State.MarkSkipped(name);
                    else
                        State.MarkExecuted(name);
                }

                foreach (var hook in _hooks)
                    hook.After(name, payload);

                double elapsed = Stopwatch.GetElapsedTime(stepT0).TotalSeconds;
                if (_observeTiming)
                    State.RecordTiming(name, elapsed);
                if (_observeLineage)
                    payload = payload.Stamp(name);
                failing = null;
            }
        }
        catch (Exception e)
        {
            if (stepT0 != 0 && stepName != null && _observeTiming)
            {
                double elapsed = Stopwatch.GetElapsedTime(stepT0).TotalSeconds;
                State.RecordTiming(stepName, elapsed);
            }
            // The failing step first, then the pipeline: OnError mirrors
            // Before/After, which fire at both levels (conformance/cases/hook.json).
            if (failing != null)
                foreach (var hook in _hooks)
                    hook.OnError(failing, e, payload);
            foreach (var hook in _hooks)
                hook.OnError(null, e, payload);
            throw;
        }

        foreach (var hook in _hooks)
            hook.After(null, payload);

        if (_guaranteeOutputKeys != null)
        {
            var data = payload.ToDict();
            var missing = _guaranteeOutputKeys.Where(k => !data.ContainsKey(k)).ToList();
            if (missing.Count > 0)
                throw new ContractViolation(
                    $"Output contract violated — missing keys: {string.Join(", ", missing.OrderBy(x => x))}");
        }

        return payload;
    }
}

/// <summary>Thrown when an input or output contract is violated.</summary>
public class ContractViolation : Exception
{
    public ContractViolation(string message) : base(message) { }
}
