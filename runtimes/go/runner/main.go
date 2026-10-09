// CUP persistent subprocess runner for Go.
// Reads length-prefixed CUP envelopes from stdin (JSON, msgpack, or shm file),
// processes them, writes results to stdout in the same format.
//
// Protocol: [4-byte LE length][payload bytes]
// Format auto-detected from first byte:
//   0x7b '{' → JSON
//   0x80-0x8f / 0xde / 0xdf → msgpack map
//   0x00      → shm file handle (msgpack {"f": "/path/cup_xxx.mp"})
//
// Usage: go run runtimes/go/runner/main.go
package main

import (
	"encoding/binary"
	"encoding/json"
	"io"
	"os"

	"github.com/vmihailenco/msgpack/v5"
)

type envelope struct {
	Data    map[string]any `json:"data" msgpack:"data"`
	TraceID string         `json:"trace_id,omitempty" msgpack:"trace_id,omitempty"`
	Lineage []string       `json:"lineage,omitempty" msgpack:"lineage,omitempty"`
}

type shmHandle struct {
	F string `msgpack:"f"`
}

// isMsgpack detects msgpack map format from the first byte.
func isMsgpack(b byte) bool {
	return (b >= 0x80 && b <= 0x8F) || b == 0xDE || b == 0xDF
}

// shmDir returns the preferred directory for shm temp files.
func shmDir() string {
	if info, err := os.Stat("/dev/shm"); err == nil && info.IsDir() {
		return "/dev/shm"
	}
	return os.TempDir()
}

func writeFrame(w *os.File, data []byte) error {
	if err := binary.Write(w, binary.LittleEndian, uint32(len(data))); err != nil {
		return err
	}
	_, err := w.Write(data)
	return err
}

func main() {
	for {
		// Read 4-byte LE length prefix
		var msgLen uint32
		if err := binary.Read(os.Stdin, binary.LittleEndian, &msgLen); err != nil {
			if err == io.EOF {
				break
			}
			os.Exit(1)
		}

		// Read message bytes
		buf := make([]byte, msgLen)
		if _, err := io.ReadFull(os.Stdin, buf); err != nil {
			os.Exit(1)
		}

		// ── Shm file mode: first byte is 0x00 ────────────────────────
		if len(buf) > 0 && buf[0] == 0x00 {
			var handle shmHandle
			if err := msgpack.Unmarshal(buf[1:], &handle); err != nil {
				os.Exit(1)
			}

			// Read payload from shm file and delete it
			fileData, err := os.ReadFile(handle.F)
			if err != nil {
				os.Exit(1)
			}
			os.Remove(handle.F)

			// Decode envelope from file (always msgpack in shm mode)
			var env envelope
			if err := msgpack.Unmarshal(fileData, &env); err != nil {
				os.Exit(1)
			}

			// Transform
			if env.Data == nil {
				env.Data = make(map[string]any)
			}
			env.Data["go_processed"] = true
			env.Data["lang"] = "go"

			// Write result to new shm file
			resultData, err := msgpack.Marshal(env)
			if err != nil {
				os.Exit(1)
			}
			tmpFile, err := os.CreateTemp(shmDir(), "cup_*.mp")
			if err != nil {
				os.Exit(1)
			}
			if _, err := tmpFile.Write(resultData); err != nil {
				os.Exit(1)
			}
			resultPath := tmpFile.Name()
			tmpFile.Close()

			// Send back shm handle
			resultHandle := shmHandle{F: resultPath}
			handleBytes, err := msgpack.Marshal(resultHandle)
			if err != nil {
				os.Exit(1)
			}
			out := append([]byte{0x00}, handleBytes...)
			if err := writeFrame(os.Stdout, out); err != nil {
				os.Exit(1)
			}
			continue
		}

		// ── JSON / msgpack mode ───────────────────────────────────────
		useMsgpack := len(buf) > 0 && isMsgpack(buf[0])

		var env envelope
		if useMsgpack {
			if err := msgpack.Unmarshal(buf, &env); err != nil {
				os.Exit(1)
			}
		} else {
			if err := json.Unmarshal(buf, &env); err != nil {
				os.Exit(1)
			}
		}

		if env.Data == nil {
			env.Data = make(map[string]any)
		}
		env.Data["go_processed"] = true
		env.Data["lang"] = "go"

		var out []byte
		var err error
		if useMsgpack {
			out, err = msgpack.Marshal(env)
		} else {
			out, err = json.Marshal(env)
		}
		if err != nil {
			os.Exit(1)
		}
		if err := writeFrame(os.Stdout, out); err != nil {
			os.Exit(1)
		}
	}
}
