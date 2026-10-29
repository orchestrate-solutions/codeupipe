package main

import (
	"path/filepath"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// A file that exists is never written over, and the command writes both
// files or neither.

func TestNothingExistsSoNothingIsRefused(t *testing.T) {
	out, refusal := runPipeline(inProject(t, nil, "filter", "Discount"))
	same(t, refusal == nil, true)
	same(t, len(Written(out)), 2)
}

func TestTheComponentThatExistsIsNamed(t *testing.T) {
	_, refusal := runPipeline(inProject(t, map[string]string{"discount_filter.go": "existing\n"},
		"filter", "Discount"))
	same(t, refusal.ExitCode, 1)
	same(t, stringsIn(refusal.Message, "discount_filter.go exists"), true)
}

func TestTheTestThatExistsIsNamedToo(t *testing.T) {
	_, refusal := runPipeline(inProject(t, map[string]string{"discount_filter_test.go": "existing\n"},
		"filter", "Discount"))
	same(t, refusal.ExitCode, 1)
	same(t, stringsIn(refusal.Message, "discount_filter_test.go exists"), true)
}

func TestBothFilesThatExistAreNamed(t *testing.T) {
	_, refusal := runPipeline(inProject(t, map[string]string{
		"discount_filter.go": "a\n", "discount_filter_test.go": "b\n"}, "filter", "Discount"))
	same(t, stringsIn(refusal.Message, "discount_filter.go exists"), true)
	same(t, stringsIn(refusal.Message, "discount_filter_test.go exists"), true)
}

// inProject gives the input of the command for a project with files, after
// the arguments and the names were read: as the steps before it would make it.
func inProject(t *testing.T, files map[string]string, args ...string) *codeupipe.Payload {
	t.Helper()
	root := t.TempDir()
	for path, text := range files {
		write(t, filepath.Join(root, path), text)
	}
	first, refusal := runStep(ParseArgumentsFilter{}, codeupipe.NewPayload(map[string]any{"root": root, "args": args}))
	if refusal != nil {
		t.Fatalf("the first step refused: %s", refusal.Message)
	}
	out, refusal := runStep(TypeNameFilter{}, first)
	if refusal != nil {
		t.Fatalf("the second step refused: %s", refusal.Message)
	}
	return out
}
