package main

import (
	"context"
	"os"
	"path/filepath"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// WriteLayoutFilter writes each file of the layout that is not there yet
// (ADD.md, "Files that exist").
//
// Filter (sync).
//
// Input keys: “root“ and “components“ (rendered).
// Output keys: “written“ and “kept“: the paths, in order, component first.
// A file that exists is kept, by itself. The directories are made before a
// file is written; one that cannot be made is refused with exit code 2.
type WriteLayoutFilter struct{}

// Call keeps the files that exist, and writes the others.
func (WriteLayoutFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	root := stringOf(payload, "root")
	components, _ := payload.Get("components").([]LaidOut)
	kept, fresh := []string{}, []file{}
	for _, component := range components {
		for _, f := range []file{{component.ComponentPath, component.ComponentText}, {component.TestPath, component.TestText}} {
			if _, err := os.Stat(filepath.Join(root, f.path)); err == nil {
				kept = append(kept, f.path)
			} else {
				fresh = append(fresh, f)
			}
		}
	}
	for _, f := range fresh {
		if err := os.MkdirAll(filepath.Dir(filepath.Join(root, f.path)), 0o755); err != nil {
			return &Refusal{ExitCode: 2, Message: "Cannot make the directory of " + f.path + ": " + err.Error()}
		}
	}
	written := []string{}
	for _, f := range fresh {
		if err := os.WriteFile(filepath.Join(root, f.path), []byte(f.text), 0o644); err != nil {
			return err
		}
		written = append(written, f.path)
	}
	payload.Insert("written", written).Insert("kept", kept)
	return nil
}
