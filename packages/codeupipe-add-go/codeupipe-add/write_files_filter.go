package main

import (
	"context"
	"os"
	"path/filepath"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// WriteFilesFilter writes the two files, and the directories that they need.
//
// Filter (sync).
//
// Input keys: “root“, “component_path“, “component_text“, “test_path“
// and “test_text“.
// Output keys: “written“ (the two paths, component first). A directory that
// cannot be made is refused with exit code 2, before a file is written.
type WriteFilesFilter struct{}

// Call makes the directories, then writes the component and its test.
func (WriteFilesFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	root := stringOf(payload, "root")
	files := []file{
		{stringOf(payload, "component_path"), stringOf(payload, "component_text")},
		{stringOf(payload, "test_path"), stringOf(payload, "test_text")},
	}
	for _, f := range files {
		if err := os.MkdirAll(filepath.Join(root, filepath.Dir(f.path)), 0o755); err != nil {
			return &Refusal{ExitCode: 2, Message: "Cannot make the directory of " + f.path + ": " + err.Error()}
		}
	}
	for _, f := range files {
		if err := os.WriteFile(filepath.Join(root, f.path), []byte(f.text), 0o644); err != nil {
			return &Refusal{ExitCode: 2, Message: "Cannot write " + f.path + ": " + err.Error()}
		}
	}
	written := []string{}
	for _, f := range files {
		written = append(written, f.path)
	}
	payload.Insert("written", written)
	return nil
}

// file is one file that the command writes: its path in the project, and its
// text.
type file struct {
	path string
	text string
}
