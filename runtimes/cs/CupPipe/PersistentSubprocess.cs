using System.Diagnostics;

namespace CupPipe;

/// <summary>
/// Fast subprocess filter that keeps the child process alive.
/// Communicates via length-prefixed stdin/stdout (CUP wire protocol).
/// Auto-restarts on child crash.
///
/// Implements IFilter so it can be used directly in a Pipeline.
/// </summary>
public sealed class PersistentSubprocess : IFilter, IDisposable
{
    private readonly string _command;
    private readonly string _args;
    private readonly string? _cwd;
    private readonly double _timeout;
    private readonly string _fmt;
    private Process? _proc;

    public PersistentSubprocess(
        string command,
        string args = "",
        string? cwd = null,
        double timeout = 30.0,
        string fmt = "json")
    {
        _command = command;
        _args = args;
        _cwd = cwd;
        _timeout = timeout;
        _fmt = fmt;
    }

    /// <summary>Sync filter call — zero asyncio overhead. IFilter implementation.</summary>
    public Payload Call(Payload payload) => Send(payload);

    /// <summary>Blocking send/receive to child process.</summary>
    public Payload Send(Payload payload)
    {
        EnsureStarted();
        var data = WireFormat.Serialize(payload, _fmt);

        try
        {
            return Exchange(data);
        }
        catch (Exception) when (_proc != null)
        {
            // Child died — restart and retry once
            KillProc();
            EnsureStarted();
            return Exchange(data);
        }
    }

    // ── Process lifecycle ───────────────────────────────────────────

    private void EnsureStarted()
    {
        if (_proc != null && !_proc.HasExited)
            return;

        _proc?.Dispose();
        _proc = null;

        var psi = new ProcessStartInfo
        {
            FileName = _command,
            Arguments = _args,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        if (_cwd != null)
            psi.WorkingDirectory = _cwd;

        _proc = Process.Start(psi)
            ?? throw new InvalidOperationException($"Failed to start: {_command} {_args}");
    }

    private Payload Exchange(byte[] data)
    {
        var stdin = _proc!.StandardInput.BaseStream;
        var stdout = _proc.StandardOutput.BaseStream;

        // Write: [4-byte LE length][data]
        var lenBytes = BitConverter.GetBytes((uint)data.Length);
        if (!BitConverter.IsLittleEndian)
            Array.Reverse(lenBytes);
        stdin.Write(lenBytes);
        stdin.Write(data);
        stdin.Flush();

        // Read: [4-byte LE length][response]
        var rawLen = ReadExact(stdout, 4);
        if (!BitConverter.IsLittleEndian)
            Array.Reverse(rawLen);
        int msgLen = (int)BitConverter.ToUInt32(rawLen);
        var response = ReadExact(stdout, msgLen);

        return WireFormat.Deserialize(response);
    }

    private static byte[] ReadExact(Stream stream, int count)
    {
        var buf = new byte[count];
        int filled = 0;
        while (filled < count)
        {
            int n = stream.Read(buf, filled, count - filled);
            if (n == 0)
                throw new IOException("Child process closed stdout");
            filled += n;
        }
        return buf;
    }

    private void KillProc()
    {
        if (_proc == null) return;
        try
        {
            _proc.Kill();
            _proc.WaitForExit(2000);
        }
        catch { /* best effort */ }
        _proc.Dispose();
        _proc = null;
    }

    public void Dispose() => KillProc();
}
