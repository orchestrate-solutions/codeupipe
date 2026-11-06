package codeupipelint

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// linted is the result of a run of the linter on files that a test wrote.
type linted struct {
	// found holds one string for each finding: "file:line rule".
	found      []string
	findings   []Finding
	suppressed int
	report     string
	exitCode   int
}

// project writes files (name to text) into a new, empty directory.
func project(t *testing.T, files map[string]string) string {
	t.Helper()
	root := t.TempDir()
	for name, text := range files {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

// lintIn writes files into a new directory and lints it.
func lintIn(t *testing.T, files map[string]string, options LintOptions) linted {
	t.Helper()
	root := project(t, files)
	run, err := LintPaths([]string{root}, options)
	if err != nil {
		t.Fatal(err)
	}
	found := []string{}
	for _, finding := range run.Findings {
		relative, _ := filepath.Rel(root, finding.Path)
		found = append(found, fmt.Sprintf("%s:%d %s", filepath.ToSlash(relative), finding.Line, finding.Rule))
	}
	return linted{found, run.Findings, len(run.Suppressed), run.Report, run.ExitCode}
}

// disable gives the options that switch rules off.
func disable(rules ...string) LintOptions {
	return LintOptions{Disable: rules}
}

// sameFound fails the test when got is not want, in order.
func sameFound(t *testing.T, got linted, want ...string) {
	t.Helper()
	if want == nil {
		want = []string{}
	}
	if fmt.Sprint(got.found) != fmt.Sprint(want) {
		t.Fatalf("found %q, want %q\n%s", got.found, want, got.report)
	}
}

// The base of the linter: a file that parses gives no finding of the rules
// that are not written yet, and a syntax error is CUP-I000.
func TestABaseRunFindsTheSyntaxError(t *testing.T) {
	got := lintIn(t, map[string]string{
		"ok.go":     "package demo\n",
		"broken.go": "package demo\n\nfunc (\n",
	}, LintOptions{})
	sameFound(t, got, "broken.go:3 CUP-I000")
	if got.exitCode != 1 {
		t.Fatalf("exit code %d, want 1", got.exitCode)
	}
}

func TestAMarkerAloneAboveAllowsTheFindingBelow(t *testing.T) {
	source := Source{Path: "x.go"}
	run := &LintRun{
		Sources:  []Source{{Path: "x.go", Markers: []Marker{{Line: 2, Col: 1, Kind: "allow-plain", Alone: true}}}},
		Findings: []Finding{{Path: source.Path, Line: 3, Rule: LogicOutsidePrimitive}, {Path: "x.go", Line: 3, Rule: LocalTypeStep}},
	}
	if err := (ApplySuppressionsFilter{}).Call(nil, run); err != nil {
		t.Fatal(err)
	}
	if len(run.Suppressed) != 1 || len(run.Findings) != 1 || run.Findings[0].Rule != LocalTypeStep {
		t.Fatalf("suppressed %v, kept %v", run.Suppressed, run.Findings)
	}
}

func TestMarkersAreReadFromComments(t *testing.T) {
	got := lintIn(t, map[string]string{"a.go": "package demo\n"}, LintOptions{})
	if got.exitCode != 0 {
		t.Fatal(got.report)
	}
	root := project(t, map[string]string{"m.go": "package demo\n\n// Doc.\n// cup: allow-plain the reason\nfunc f() {} // cup: allow-name x\n\nvar s = \"// cup: allow-plain in a string\"\n"})
	run, err := LintPaths([]string{root}, LintOptions{})
	if err != nil {
		t.Fatal(err)
	}
	markers := run.Sources[0].Markers
	want := "[{4 4 allow-plain true} {5 16 allow-name false}]"
	if fmt.Sprint(markers) != want {
		t.Fatalf("markers %v, want %s", markers, want)
	}
}
