package main

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

func write(t *testing.T, path, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

func same(t *testing.T, got, want any) {
	t.Helper()
	if !deepEqual(got, want) {
		t.Fatalf("got %#v, want %#v", got, want)
	}
}

func deepEqual(got, want any) bool {
	return reflect.DeepEqual(got, want)
}

// text gives the text of one key of a Payload.
func text(payload *codeupipe.Payload, key string) string {
	value, _ := payload.Get(key).(string)
	return value
}

// newInput gives the input of the command after the first two steps, for a
// project with root, a directory and a file name.
func newInput(root, directory, snake string) *codeupipe.Payload {
	return codeupipe.NewPayload(map[string]any{"root": root, "directory": directory, "snake": snake})
}

// moduleText gives the text of a go.mod with that module.
func moduleText(module string) string {
	if module == "" {
		return ""
	}
	return "module " + module + "\n\ngo 1.22\n"
}

// stringsIn says whether text has the part.
func stringsIn(text, part string) bool {
	return strings.Contains(text, part)
}

// runStep runs one step of the command on a Payload, and gives the same
// Payload back, or the Refusal that the step gave.
func runStep(step codeupipe.Filter, in *codeupipe.Payload) (*codeupipe.Payload, *Refusal) {
	err := step.Call(context.Background(), in)
	if err != nil {
		var refusal *Refusal
		if !errors.As(err, &refusal) {
			return nil, &Refusal{ExitCode: 2, Message: err.Error()}
		}
		return nil, refusal
	}
	return in, nil
}
