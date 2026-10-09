/**
 * CUP persistent subprocess runner for TypeScript/Node.
 * Reads length-prefixed CUP envelopes from stdin (JSON, msgpack, or shm file),
 * processes them, writes results to stdout in the same format.
 *
 * Protocol: [4-byte LE length][payload bytes]
 * Format auto-detected from first byte:
 *   0x7b '{' → JSON
 *   0x80-0x8f / 0xde / 0xdf → msgpack map
 *   0x00      → shm file handle (msgpack {"f": "/path/cup_xxx.mp"})
 *
 * Usage: node runtimes/ts/runner.js
 */

import { readFileSync, writeFileSync, unlinkSync, statSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { randomBytes } from "crypto";

let msgpackLib = null;
try {
  msgpackLib = await import("@msgpack/msgpack");
} catch (_) {
  // msgpack not installed — JSON-only mode (shm requires msgpack)
}

const stdin = process.stdin;
const stdout = process.stdout;

// Prefer /dev/shm (Linux tmpfs = RAM) over system tmpdir
function getShmDir() {
  try {
    statSync("/dev/shm");
    return "/dev/shm";
  } catch (_) {
    return tmpdir();
  }
}
const shmDir = getShmDir();

let buffer = Buffer.alloc(0);

/**
 * Detect msgpack map format from first byte.
 */
function isMsgpack(buf) {
  if (buf.length === 0) return false;
  const b = buf[0];
  return (b >= 0x80 && b <= 0x8f) || b === 0xde || b === 0xdf;
}

stdin.on("data", (chunk) => {
  buffer = Buffer.concat([buffer, chunk]);
  processBuffer();
});

stdin.on("end", () => {
  process.exit(0);
});

function processBuffer() {
  while (true) {
    if (buffer.length < 4) return;

    const msgLen = buffer.readUInt32LE(0);
    if (buffer.length < 4 + msgLen) return;

    const msgBytes = buffer.subarray(4, 4 + msgLen);
    buffer = buffer.subarray(4 + msgLen);

    // ── Shm file mode ──────────────────────────────────────────────
    if (msgpackLib && msgBytes.length > 0 && msgBytes[0] === 0x00) {
      const handle = msgpackLib.decode(msgBytes.slice(1));
      const filePath = handle.f;
      const fileData = readFileSync(filePath);
      try { unlinkSync(filePath); } catch (_) {}

      const envelope = msgpackLib.decode(fileData);
      if (!envelope.data) envelope.data = {};
      envelope.data.ts_processed = true;
      envelope.data.lang = "ts";

      const resultData = Buffer.from(msgpackLib.encode(envelope));
      const resultPath = join(shmDir, "cup_" + randomBytes(8).toString("hex") + ".mp");
      writeFileSync(resultPath, resultData);

      const resultHandle = msgpackLib.encode({ f: resultPath });
      const out = Buffer.concat([Buffer.from([0x00]), Buffer.from(resultHandle)]);
      const lenBuf = Buffer.alloc(4);
      lenBuf.writeUInt32LE(out.length, 0);
      stdout.write(lenBuf);
      stdout.write(out);
      continue;
    }

    // ── JSON / msgpack mode ────────────────────────────────────────
    const useMsgpack = msgpackLib && isMsgpack(msgBytes);

    let envelope;
    if (useMsgpack) {
      envelope = msgpackLib.decode(msgBytes);
    } else {
      envelope = JSON.parse(msgBytes.toString("utf-8"));
    }

    if (!envelope.data) envelope.data = {};
    envelope.data.ts_processed = true;
    envelope.data.lang = "ts";

    let out;
    if (useMsgpack) {
      out = Buffer.from(msgpackLib.encode(envelope));
    } else {
      out = Buffer.from(JSON.stringify(envelope), "utf-8");
    }

    const lenBuf = Buffer.alloc(4);
    lenBuf.writeUInt32LE(out.length, 0);
    stdout.write(lenBuf);
    stdout.write(out);
  }
}
