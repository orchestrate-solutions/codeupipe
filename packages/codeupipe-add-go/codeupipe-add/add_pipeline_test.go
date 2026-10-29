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

// add runs the command in a project of its own, and gives what happened:
// the exit code, what the command printed, and the files that it made.
func add(t *testing.T, args ...string) runResult {
	t.Helper()
	root := t.TempDir()
	return runIn(t, root, args...)
}

// project makes a project with the files that a case gives before the
// command runs, and runs the command in it.
func project(t *testing.T, given map[string]string, args ...string) runResult {
	t.Helper()
	root := t.TempDir()
	for path, text := range given {
		write(t, filepath.Join(root, path), text)
	}
	return runIn(t, root, args...)
}

func runIn(t *testing.T, root string, args ...string) runResult {
	t.Helper()
	stdout, stderr := tempFile(t), tempFile(t)
	code := run(args, stdout, stderr, root)
	return runResult{
		Exit:    code,
		Stdout:  readAll(t, stdout),
		Stderr:  readAll(t, stderr),
		Written: lines(readAll(t, stdout)),
		Root:    root,
	}
}

// runResult is what one run of the command did.
type runResult struct {
	Exit    int
	Stdout  string
	Stderr  string
	Written []string
	Root    string
}

// text gives the text of one file that the command made, by its path.
func (r runResult) text(t *testing.T, path string) string {
	t.Helper()
	body, err := os.ReadFile(filepath.Join(r.Root, path))
	if err != nil {
		t.Fatalf("cannot read %s: %s", path, err)
	}
	return string(body)
}

func write(t *testing.T, path, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

func tempFile(t *testing.T) *os.File {
	t.Helper()
	file, err := os.CreateTemp(t.TempDir(), "cup-add")
	if err != nil {
		t.Fatal(err)
	}
	return file
}

func readAll(t *testing.T, file *os.File) string {
	t.Helper()
	if _, err := file.Seek(0, 0); err != nil {
		t.Fatal(err)
	}
	body, err := os.ReadFile(file.Name())
	if err != nil {
		t.Fatal(err)
	}
	return string(body)
}

func lines(text string) []string {
	out := []string{}
	for _, line := range strings.Split(text, "\n") {
		if strings.TrimSpace(line) != "" {
			out = append(out, line)
		}
	}
	return out
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

// foundIn says whether the file at path has the text.
func foundIn(t *testing.T, r runResult, path, want string) bool {
	t.Helper()
	return strings.Contains(r.text(t, path), want)
}

// stringsIn says whether text has the part.
func stringsIn(text, part string) bool {
	return strings.Contains(text, part)
}

// exists says whether the project has the file.
func exists(r runResult, path string) bool {
	_, err := os.Stat(filepath.Join(r.Root, path))
	return err == nil
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
