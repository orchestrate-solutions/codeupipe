package main

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// writtenIn gives the paths that WriteFilesFilter made in a project, and the
// exit code and the message of a refusal.
func writtenIn(t *testing.T, files map[string]string, args ...string) (paths []string, code int, stderr string, root string) {
	t.Helper()
	root = t.TempDir()
	for path, text := range files {
		write(t, filepath.Join(root, path), text)
	}
	out, refusal := runPipeline(codeupipe.NewPayload(map[string]any{"root": root, "args": args,
		"module": "pricing"}))
	if refusal != nil {
		return nil, refusal.ExitCode, refusal.Message, root
	}
	return Written(out), 0, "", root
}

func TestItMakesTheTwoFilesWithTheirText(t *testing.T) {
	paths, code, _, root := writtenIn(t, nil, "filter", "Discount")
	same(t, code, 0)
	same(t, paths, []string{"discount_filter.go", "discount_filter_test.go"})
	body, err := os.ReadFile(filepath.Join(root, "discount_filter.go"))
	same(t, err == nil, true)
	same(t, stringsIn(string(body), "type DiscountFilter struct{}"), true)
}

func TestItMakesADirectoryThatIsNotThere(t *testing.T) {
	paths, code, _, root := writtenIn(t, nil, "filter", "Discount", "src/pricing")
	same(t, code, 0)
	same(t, paths, []string{"src/pricing/discount_filter.go", "src/pricing/discount_filter_test.go"})
	_, err := os.Stat(filepath.Join(root, "src/pricing"))
	same(t, err == nil, true)
}

func TestItWritesNeitherFileWhenOneExists(t *testing.T) {
	_, code, stderr, root := writtenIn(t, map[string]string{"discount_filter_test.go": "existing\n"},
		"filter", "Discount")
	same(t, code, 1)
	same(t, stringsIn(stderr, "exists"), true)
	_, err := os.Stat(filepath.Join(root, "discount_filter.go"))
	same(t, os.IsNotExist(err), true)
}

func TestTheWrittenPathsAreRelativeToTheRoot(t *testing.T) {
	paths, _, _, root := writtenIn(t, nil, "tap", "Audit", "src/pricing")
	for _, path := range paths {
		same(t, filepath.IsAbs(path), false)
		same(t, stringsIn(path, root), false)
	}
}
