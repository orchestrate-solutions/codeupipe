package main

import (
	"context"
	"os"
	"path/filepath"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// RefuseExistingFilter checks the two files before the command writes one, so
// that it writes both or neither (ADD.md).
//
// Filter (sync).
//
// Input keys: “root“, “component_path“, “test_path“.
// Output keys: none. When either file exists, it refuses with exit code 1 and
// names each file that exists, with the word “exists“.
type RefuseExistingFilter struct{}

// Call looks at both files, and refuses with the list of those that exist.
func (RefuseExistingFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	root, _ := payload.Get("root").(string)
	paths := []string{}
	for _, path := range []string{stringOf(payload, "component_path"), stringOf(payload, "test_path")} {
		if _, err := os.Stat(filepath.Join(root, path)); err == nil {
			paths = append(paths, path)
		}
	}
	if len(paths) > 0 {
		lines := make([]string, len(paths))
		for i, path := range paths {
			lines[i] = path + " exists"
		}
		return &Refusal{ExitCode: 1, Message: strings.Join(lines, "\n")}
	}
	return nil
}

func stringOf(payload *codeupipe.Payload, key string) string {
	value, _ := payload.Get(key).(string)
	return value
}
