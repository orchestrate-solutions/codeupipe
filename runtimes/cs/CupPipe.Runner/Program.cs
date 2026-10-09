// CUP persistent subprocess runner for C#.
// Reads length-prefixed CUP envelopes from stdin (JSON or msgpack),
// processes them, writes results to stdout in the same format.
//
// Protocol: [4-byte LE length][payload bytes]
// Format auto-detected from first byte:
//   0x7b '{' → JSON
//   0x80-0x8f / 0xde / 0xdf → msgpack map
//   0x00      → shm file handle (msgpack {"f": "/path/cup_xxx.mp"})
//
// Build: dotnet build runtimes/cs/CupPipe.Runner -c Release
// Usage: dotnet run --project runtimes/cs/CupPipe.Runner

using CupPipe;

var stdin = Console.OpenStandardInput();
var stdout = Console.OpenStandardOutput();
var counter = 0;

while (true)
{
    // Read 4-byte LE length prefix
    var lenBuf = new byte[4];
    if (!TryReadExact(stdin, lenBuf))
        break; // EOF — clean exit

    if (!BitConverter.IsLittleEndian)
        Array.Reverse(lenBuf);
    int msgLen = (int)BitConverter.ToUInt32(lenBuf);

    // Read message bytes
    var msgBuf = new byte[msgLen];
    if (!TryReadExact(stdin, msgBuf))
        break;

    byte[] outBytes;

    // ── Shm file mode: first byte is 0x00 ────────────────────────
    if (msgBuf.Length > 0 && msgBuf[0] == 0x00)
    {
        // Decode shm handle (msgpack after sentinel)
        int offset = 1;
        var handle = CupPipe.MsgpackReader.ReadObject(msgBuf, ref offset) as Dictionary<string, object?>;
        var path = handle?["f"]?.ToString()
            ?? throw new InvalidOperationException("Missing 'f' in shm handle");

        // Read payload from file and delete it
        var fileData = File.ReadAllBytes(path);
        try { File.Delete(path); } catch { }

        // Decode envelope (always msgpack in shm files)
        int envOffset = 0;
        var envelope = CupPipe.MsgpackReader.ReadObject(fileData, ref envOffset) as Dictionary<string, object?>;
        if (envelope == null)
            throw new InvalidOperationException("Failed to decode shm envelope");

        // Transform: add markers
        var data = envelope.TryGetValue("data", out var d) && d is Dictionary<string, object?> dd
            ? dd : new Dictionary<string, object?>();
        data["csharp_processed"] = true;
        data["lang"] = "csharp";
        envelope["data"] = data;

        // Write result to new shm file
        using var envMs = new MemoryStream();
        CupPipe.MsgpackWriter.WriteMap(envMs, envelope);
        var resultData = envMs.ToArray();

        var shmDir = Directory.Exists("/dev/shm") ? "/dev/shm" : Path.GetTempPath();
        var resultPath = Path.Combine(shmDir, $"cup_{Environment.ProcessId}_{counter++}.mp");
        File.WriteAllBytes(resultPath, resultData);

        // Send back shm handle
        var resultHandle = new Dictionary<string, object?> { ["f"] = resultPath };
        using var hMs = new MemoryStream();
        CupPipe.MsgpackWriter.WriteMap(hMs, resultHandle);
        var handleBytes = hMs.ToArray();

        var shmOut = new byte[1 + handleBytes.Length];
        shmOut[0] = 0x00;
        Array.Copy(handleBytes, 0, shmOut, 1, handleBytes.Length);

        WriteFrame(stdout, shmOut);
        continue;
    }

    // ── JSON / msgpack mode ──────────────────────────────────────
    bool useMsgpack = msgBuf.Length > 0 && WireFormat.IsMsgpackMap(msgBuf[0]);

    var payload = useMsgpack
        ? WireFormat.Deserialize(msgBuf, "msgpack")
        : WireFormat.Deserialize(msgBuf, "json");

    // Transform: echo + add markers
    payload = payload.Insert("csharp_processed", true);
    payload = payload.Insert("lang", "csharp");

    outBytes = useMsgpack
        ? WireFormat.Serialize(payload, "msgpack")
        : WireFormat.Serialize(payload, "json");

    WriteFrame(stdout, outBytes);
}

// ── Helpers ─────────────────────────────────────────────────────────

static bool TryReadExact(Stream stream, byte[] buffer)
{
    int filled = 0;
    while (filled < buffer.Length)
    {
        int n = stream.Read(buffer, filled, buffer.Length - filled);
        if (n == 0) return false; // EOF
        filled += n;
    }
    return true;
}

static void WriteFrame(Stream stream, byte[] data)
{
    var lenBytes = BitConverter.GetBytes((uint)data.Length);
    if (!BitConverter.IsLittleEndian)
        Array.Reverse(lenBytes);
    stream.Write(lenBytes);
    stream.Write(data);
    stream.Flush();
}
