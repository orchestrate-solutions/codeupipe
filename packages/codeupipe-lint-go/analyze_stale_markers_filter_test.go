package codeupipelint

import (
	"strings"
	"testing"
)

// A comment that allows nothing is a warning, at the line and column of the comment.
func TestAMarkerThatAllowsNothingIsAWarning(t *testing.T) {
	got := lintIn(t, map[string]string{"add.go": `package demo

// cup: allow-plain it had a loop before
func add(a, b int) int { return a + b }
var one = 1 // cup: allow-state-read nothing here reads State
/*
 * cup: allow-plian a kind that does not exist
 */
var two = 2
// cup: allow-outside-write Go has no such rule
var three = 3
`}, LintOptions{})
	sameFound(t, got,
		"add.go:3 CUP-I009",
		"add.go:5 CUP-I009",
		"add.go:7 CUP-I009",
		"add.go:10 CUP-I009")
	if !got.findings[0].Warning {
		t.Fatal("CUP-I009 is not a warning")
	}
	if !strings.HasPrefix(got.findings[0].Message, "The comment `cup: allow-plain` allows nothing. Remove it") {
		t.Fatalf("message %q", got.findings[0].Message)
	}
	if got.findings[1].Col != 16 {
		t.Fatalf("column %d, want 16", got.findings[1].Col)
	}
	if got.exitCode != 0 {
		t.Fatalf("exit code %d, want 0", got.exitCode)
	}
	strict := lintIn(t, map[string]string{"one.go": "package demo\n\n// cup: allow-plain no reason\nvar one = 1\n"}, LintOptions{Strict: true})
	if strict.exitCode != 1 {
		t.Fatalf("strict exit code %d, want 1", strict.exitCode)
	}
}

// A comment that allows a finding is not reported. Text that only names a marker is not a comment.
func TestAMarkerThatAllowsAFindingIsNotReported(t *testing.T) {
	got := lintIn(t, map[string]string{"pick.go": `package demo

// cup: allow-plain the entry of the program
func pick(list []int) int {
	for _, each := range list {
		if each > 0 {
			return each
		}
	}
	return 0
}

func choose(flag bool) int { // cup: allow-plain a small helper
	if flag {
		return 1
	}
	return 2
}

var help = "say why: // cup: allow-plain <reason>"
var slash = '/' // a char, then cup: allow-plain is not at the start
`}, LintOptions{})
	sameFound(t, got)
	if got.suppressed != 2 {
		t.Fatalf("suppressed %d, want 2", got.suppressed)
	}
}

// A comment for a rule that is switched off is not reported.
func TestAMarkerForASwitchedOffRuleIsNotReported(t *testing.T) {
	off := lintIn(t, map[string]string{"pick.go": "package demo\n\n// cup: allow-plain the entry\nfunc pick(flag bool) int {\n\tif flag {\n\t\treturn 1\n\t}\n\treturn 2\n}\n"},
		disable(LogicOutsidePrimitive))
	sameFound(t, off)
	if off.suppressed != 0 {
		t.Fatalf("suppressed %d, want 0", off.suppressed)
	}
	quiet := lintIn(t, map[string]string{"one.go": "package demo\n\n// cup: allow-plain no reason\nvar one = 1\n"},
		disable(MarkerAllowsNothing))
	sameFound(t, quiet)
}
