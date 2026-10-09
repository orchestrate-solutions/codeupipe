namespace CupPipe;

/// <summary>
/// Processing unit — takes a payload in, returns a transformed payload out.
/// Sync-first by design. See also: TypeScript, Python, Rust, Go implementations.
/// </summary>
public interface IFilter
{
    Payload Call(Payload payload);
}

/// <summary>
/// Non-modifying observation point — inspect the payload without changing it.
/// </summary>
public interface ITap
{
    void Observe(Payload payload);
}

/// <summary>
/// Lifecycle hook — before / after / on_error (optional overrides).
/// </summary>
public abstract class Hook
{
    /// <summary><paramref name="step"/> is the step's identity; null for the pipeline.</summary>
    public virtual void Before(string? step, Payload payload) { }
    public virtual void After(string? step, Payload payload) { }
    public virtual void OnError(string? step, Exception error, Payload payload) { }
}
