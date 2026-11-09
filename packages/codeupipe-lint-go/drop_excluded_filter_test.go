package codeupipelint

import (
	"context"
	"fmt"
	"testing"
)

// The globs of Exclude follow Python's fnmatch, as the Rust linter has them.
func TestGlobMatchesAsAShellGlob(t *testing.T) {
	var filter DropExcludedFilter
	check := func(path, pattern string, want bool) {
		t.Helper()
		if got := filter.glob(path, pattern); got != want {
			t.Errorf("glob(%q, %q) = %v, want %v", path, pattern, got, want)
		}
	}
	check("src/generated/x.go", "*/generated/*", true)
	check("a/b.go", "*.go", true)
	check("a/b.go", "*.ts", false)
	check("x1.go", "x?.go", true)
	check("xb.go", "x[abc].go", true)
	check("xd.go", "x[abc].go", false)
	check("xd.go", "x[!abc].go", true)
	check("x5.go", "x[0-9].go", true)
	check("x[.go", "x[.go", true)
	check("discount.go", "*/discount.go", false)
}

func TestDropExcludedDropsTheFilesThatMatchAGlob(t *testing.T) {
	run := &LintRun{
		Files:   []string{"discount.go", "set_filter.go", "gen/x.go", "other/y.go"},
		Exclude: []string{"discount.go", "*/x.go"},
	}
	if err := (DropExcludedFilter{}).Call(context.Background(), run); err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprint(run.Files); got != "[set_filter.go other/y.go]" {
		t.Fatalf("files %s", got)
	}
}

func TestDropExcludedKeepsEveryFileWithNoGlob(t *testing.T) {
	run := &LintRun{Files: []string{"a.go", "b.go"}}
	if err := (DropExcludedFilter{}).Call(context.Background(), run); err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprint(run.Files); got != "[a.go b.go]" {
		t.Fatalf("files %s", got)
	}
}

func TestAnExcludedFileIsNotChecked(t *testing.T) {
	files := map[string]string{"ok.go": "package demo\n", "broken.go": "package demo\n\nfunc (\n"}
	sameFound(t, lintIn(t, files, LintOptions{}), "broken.go:3 CUP-I000")
	sameFound(t, lintIn(t, files, LintOptions{Exclude: []string{"*/broken.go"}}))
}
