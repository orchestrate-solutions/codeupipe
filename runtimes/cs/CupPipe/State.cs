namespace CupPipe;

/// <summary>
/// Pipeline execution state — tracks what happened during a run.
/// </summary>
public sealed class State
{
    public List<string> Executed { get; } = new();
    public List<string> Skipped { get; } = new();
    public List<(string Name, Exception Error)> Errors { get; } = new();
    public Dictionary<string, double> Timings { get; } = new();

    public void MarkExecuted(string name) => Executed.Add(name);
    public void MarkSkipped(string name) => Skipped.Add(name);
    public void RecordTiming(string name, double seconds) => Timings[name] = seconds;
    public void RecordError(string name, Exception error) => Errors.Add((name, error));
}
