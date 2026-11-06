package codeupipelint

import (
	"context"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// CollectFilesFilter gives the Go files under the given paths.
//
// Reads Paths (files or directories). Writes Files, and Errors for a path
// that is not there. Directories are walked in the order of their names.
// As the go command does, it skips the directories "testdata" and "vendor",
// and each directory whose name starts with "." or "_".
type CollectFilesFilter struct{}

func (CollectFilesFilter) Call(ctx context.Context, run *LintRun) error {
	var found []string
	for _, root := range run.Paths {
		info, err := os.Stat(root)
		switch {
		case err != nil:
			run.Errors = append(run.Errors, root+": no such file or directory")
		case info.IsDir():
			found = append(found, walkGoFiles(root)...)
		case strings.HasSuffix(root, ".go"):
			found = append(found, filepath.Clean(root))
		}
	}
	run.Files = found
	return nil
}

// walkGoFiles gives the .go files under directory, in the order of their
// names.
// cup: allow-plain shared by the Filters: a walk of the disk
func walkGoFiles(directory string) []string {
	entries, err := os.ReadDir(directory)
	if err != nil {
		return nil
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name() < entries[j].Name() })
	var found []string
	for _, entry := range entries {
		name := entry.Name()
		path := filepath.Join(directory, name)
		if entry.IsDir() {
			if name != "testdata" && name != "vendor" && !strings.HasPrefix(name, ".") && !strings.HasPrefix(name, "_") {
				found = append(found, walkGoFiles(path)...)
			}
		} else if strings.HasSuffix(name, ".go") {
			found = append(found, path)
		}
	}
	return found
}
