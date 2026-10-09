"""
CUP persistent subprocess runner for Python.
Reads length-prefixed CUP envelopes from stdin (JSON, msgpack, or shm file),
processes them, writes results to stdout in the same format.

Protocol: [4-byte LE length][payload bytes]
Format auto-detected from first byte:
  0x7b '{' → JSON
  0x80-0x8f / 0xde / 0xdf → msgpack map
  0x00      → shm file handle (msgpack {"f": "/path/cup_xxx.mp"})

Usage: python runtimes/py/runner.py
"""

import json
import os
import struct
import sys
import tempfile

try:
    import msgpack
    _HAS_MSGPACK = True
except ImportError:
    _HAS_MSGPACK = False

_SHM_DIR = "/dev/shm" if os.path.isdir("/dev/shm") else tempfile.gettempdir()
_SHM_SENTINEL = 0x00


def _is_msgpack(data: bytes) -> bool:
    if not data:
        return False
    b = data[0]
    return (0x80 <= b <= 0x8F) or b == 0xDE or b == 0xDF


def _decode_plain(data: bytes):
    """Decode JSON or msgpack envelope. Returns (envelope, use_msgpack)."""
    if _HAS_MSGPACK and _is_msgpack(data):
        return msgpack.unpackb(data, raw=False), True
    return json.loads(data), False


def _decode_shm(data: bytes):
    """Read envelope from shm file referenced by wire bytes."""
    handle = msgpack.unpackb(data[1:], raw=False)
    path = handle["f"]
    with open(path, "rb") as f:
        body = f.read()
    try:
        os.unlink(path)
    except OSError:
        pass
    return msgpack.unpackb(body, raw=False), True


def _encode_plain(envelope: dict, use_msgpack: bool) -> bytes:
    if use_msgpack and _HAS_MSGPACK:
        return msgpack.packb(envelope, use_bin_type=True)
    return json.dumps(envelope).encode("utf-8")


def _encode_shm(envelope: dict) -> bytes:
    """Write envelope to shm file, return sentinel + msgpack handle bytes."""
    body = msgpack.packb(envelope, use_bin_type=True)
    fd, path = tempfile.mkstemp(prefix="cup_", dir=_SHM_DIR, suffix=".mp")
    os.write(fd, body)
    os.close(fd)
    handle = msgpack.packb({"f": path}, use_bin_type=True)
    return bytes([_SHM_SENTINEL]) + handle


def main():
    while True:
        raw_len = sys.stdin.buffer.read(4)
        if len(raw_len) < 4:
            break

        msg_len = struct.unpack("<I", raw_len)[0]
        data = sys.stdin.buffer.read(msg_len)

        # Detect format from first byte
        use_shm = _HAS_MSGPACK and len(data) > 0 and data[0] == _SHM_SENTINEL

        if use_shm:
            envelope, is_mp = _decode_shm(data)
        else:
            envelope, is_mp = _decode_plain(data)

        if "data" not in envelope or envelope["data"] is None:
            envelope["data"] = {}
        envelope["data"]["py_processed"] = True
        envelope["data"]["lang"] = "python"

        if use_shm:
            out = _encode_shm(envelope)
        else:
            out = _encode_plain(envelope, is_mp)

        sys.stdout.buffer.write(struct.pack("<I", len(out)) + out)
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
