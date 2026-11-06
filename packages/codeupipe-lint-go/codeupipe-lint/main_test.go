// The command: its exit codes, arguments, config file, and --exclude. The
// tests run the built command, as a user does.
package main

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// binary is the command, built once by TestMain.
var binary string

// broken does not parse: one finding, CUP-I000, at line 3.
const broken = "package demo\n\nfunc (\n"

// clean has no finding.
const clean = "package demo\n"

// rulesText is the output of --rules: each rule, in the order of its id.
const rulesText = `CUP-A001  function-step
CUP-A003  local-type-step
CUP-A005  unnamed-pipeline-step
CUP-A008  function-predicate
CUP-I000  parse-error
CUP-I003  state-read-in-step
CUP-I004  write-outside-filter
CUP-I005  one-primitive-per-file
CUP-I006  primitive-file-name
CUP-I007  primitive-role-suffix
CUP-I008  logic-outside-primitive
CUP-I009  marker-allows-nothing
`

// TestMain builds the command once, and runs the tests.
func TestMain(m *testing.M) {
	dir, err := os.MkdirTemp("", "codeupipe-lint-test")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	binary = filepath.Join(dir, "codeupipe-lint")
	build := exec.Command("go", "build", "-o", binary, ".")
	build.Stderr = os.Stderr
	if err := build.Run(); err != nil {
		fmt.Fprintln(os.Stderr, "build:", err)
		os.RemoveAll(dir)
		os.Exit(1)
	}
	code := m.Run()
	os.RemoveAll(dir)
	os.Exit(code)
}

// result is what one run of the command gave.
type result struct {
	code int
	out  string
	err  string
}

// execute runs the command in dir with args.
func execute(t *testing.T, dir string, args ...string) result {
	t.Helper()
	cmd := exec.Command(binary, args...)
	cmd.Dir = dir
	var out, stderr bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &stderr
	code := 0
	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if !errors.As(err, &exitErr) {
			t.Fatal(err)
		}
		code = exitErr.ExitCode()
	}
	return result{code, out.String(), stderr.String()}
}

// writeProject writes files (name to text) into a new, empty directory.
func writeProject(t *testing.T, files map[string]string) string {
	t.Helper()
	root := t.TempDir()
	for name, text := range files {
		if err := os.WriteFile(filepath.Join(root, name), []byte(text), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

func TestExitCode0WithNoFindingsAndExitCode1WithAFinding(t *testing.T) {
	clean0 := execute(t, writeProject(t, map[string]string{"ok.go": clean}), "ok.go")
	if clean0.code != 0 || clean0.out != "No findings.\n" {
		t.Fatalf("exit %d, out %q", clean0.code, clean0.out)
	}
	bad := execute(t, writeProject(t, map[string]string{"broken.go": broken}), ".")
	if bad.code != 1 {
		t.Fatalf("exit %d, want 1: %s", bad.code, bad.out)
	}
	if !strings.HasPrefix(bad.out, "broken.go:3:") || !strings.Contains(bad.out, " CUP-I000 parse-error  ") {
		t.Fatalf("out %q", bad.out)
	}
	if !strings.HasSuffix(bad.out, "\n1 finding.\n") {
		t.Fatalf("out %q, want the summary", bad.out)
	}
}

func TestExitCode2ForAPathThatIsNotThereARuleThatIsNotKnownAndNoPaths(t *testing.T) {
	dir := writeProject(t, nil)
	cases := []struct {
		name   string
		args   []string
		stderr string
	}{
		{"a path that is not there", []string{"nothing-here"}, "error: nothing-here: no such file or directory"},
		{"a rule that is not known", []string{"--disable", "CUP-X999", "."}, "error: no such rule: CUP-X999 (the rules are listed by --rules)"},
		{"a rule that the Go compiler checks", []string{"--disable", "CUP-A002", "."}, "error: no such rule: CUP-A002"},
		{"no paths and no config file", nil, "error: give at least one path"},
		{"an option that is not known", []string{"--nope", "."}, "error: unknown option '--nope'"},
		{"an option with no value", []string{"--exclude"}, "error: option '--exclude' needs a value"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := execute(t, dir, c.args...)
			if got.code != 2 || !strings.Contains(got.err, c.stderr) {
				t.Fatalf("exit %d, stderr %q, want %q", got.code, got.err, c.stderr)
			}
		})
	}
}

func TestRulesListsTheRuleIDs(t *testing.T) {
	got := execute(t, writeProject(t, nil), "--rules")
	if got.code != 0 || got.out != rulesText {
		t.Fatalf("exit %d, out %q", got.code, got.out)
	}
}

func TestExcludeAndDisable(t *testing.T) {
	dir := writeProject(t, map[string]string{"broken.go": broken})
	if got := execute(t, dir, "--exclude", "*/broken.go", "--exclude", "broken.go", "."); got.code != 0 {
		t.Fatalf("two excludes: exit %d", got.code)
	}
	if got := execute(t, dir, "--exclude=broken.go", "."); got.code != 0 {
		t.Fatalf("exclude with =: exit %d", got.code)
	}
	if got := execute(t, dir, "--exclude", "*/broken.go", "."); got.code != 1 {
		t.Fatalf("a glob that does not match: exit %d, want 1", got.code)
	}
	if got := execute(t, dir, "--disable", "CUP-I000", "--disable=CUP-I007", "."); got.code != 0 {
		t.Fatalf("disable the parse error: exit %d", got.code)
	}
	if got := execute(t, dir, "--disable", "CUP-I007", "."); got.code != 1 {
		t.Fatalf("disable another rule: exit %d, want 1", got.code)
	}
}

func TestStrictWithNoWarning(t *testing.T) {
	dir := writeProject(t, map[string]string{"ok.go": clean})
	if got := execute(t, dir, "--strict", "."); got.code != 0 {
		t.Fatalf("exit %d", got.code)
	}
}

// A warning fails the run only with --strict.
func TestStrictMakesAWarningFail(t *testing.T) {
	dir := writeProject(t, map[string]string{
		"plain.go": "package demo\n\nfunc plain(n int) int {\n\tif n > 0 {\n\t\treturn n\n\t}\n\treturn 0\n}\n",
	})
	if got := execute(t, dir, "."); got.code != 0 {
		t.Fatalf("a warning without --strict: exit %d, want 0", got.code)
	}
	if got := execute(t, dir, "--strict", "."); got.code != 1 {
		t.Fatalf("a warning with --strict: exit %d, want 1", got.code)
	}
}

func TestWithNoPathsTheyComeFromTheConfigFile(t *testing.T) {
	dir := writeProject(t, map[string]string{
		"broken.go":       broken,
		"cup.config.json": `{"lint": {"paths": ["."], "disable": ["CUP-I000"]}, "deploy": {}}`,
	})
	if got := execute(t, dir); got.code != 0 {
		t.Fatalf("config paths and disable: exit %d, want 0", got.code)
	}
	// A path that someone names is checked, whatever the file says.
	if got := execute(t, dir, "broken.go"); got.code != 1 {
		t.Fatalf("a named path: exit %d, want 1", got.code)
	}
}

func TestAnOptionThatIsGivenWinsOverTheFile(t *testing.T) {
	dir := writeProject(t, map[string]string{
		"broken.go":       broken,
		"cup.config.json": `{"lint": {"paths": ["."], "exclude": ["broken.go"]}}`,
	})
	if got := execute(t, dir); got.code != 0 {
		t.Fatalf("config exclude: exit %d, want 0", got.code)
	}
	if got := execute(t, dir, "--exclude", "other.go"); got.code != 1 {
		t.Fatalf("--exclude given: exit %d, want 1", got.code)
	}
}

func TestAConfigFileThatIsWrong(t *testing.T) {
	cases := []struct {
		text   string
		stderr string
	}{
		{`{"lint": {"path": ["."]}}`, "unknown key 'path'"},
		{`{"lint": {"paths": "."}}`, "lint.paths must be a list of strings"},
		{`{"lint": {"paths": ["."], "disable": ["CUP-X999"]}}`, "no such rule: CUP-X999"},
		{`{"lint": `, "is not valid JSON"},
	}
	for _, c := range cases {
		dir := writeProject(t, map[string]string{"cup.config.json": c.text})
		got := execute(t, dir)
		if got.code != 2 || !strings.Contains(got.err, c.stderr) {
			t.Fatalf("%s: exit %d, stderr %q, want %q", c.text, got.code, got.err, c.stderr)
		}
	}
}

func TestTheConfigFlagNamesAnotherFile(t *testing.T) {
	dir := writeProject(t, map[string]string{
		"broken.go": broken,
		"alt.json":  `{"lint": {"paths": ["."]}}`,
	})
	if got := execute(t, dir, "--config=alt.json"); got.code != 1 {
		t.Fatalf("--config=: exit %d, want 1", got.code)
	}
	got := execute(t, dir, "--config", "other.json")
	if got.code != 2 || !strings.Contains(got.err, "other.json: no such file") {
		t.Fatalf("missing --config file: exit %d, stderr %q", got.code, got.err)
	}
}
