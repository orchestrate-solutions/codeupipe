package codeupipelint

import (
	"fmt"
	"strings"
	"testing"
)

// flaggedNames gives the part of each warning before " has logic".
func flaggedNames(out linted) []string {
	var names []string
	for _, finding := range out.findings {
		if finding.Warning {
			names = append(names, strings.Split(finding.Message, " has logic")[0])
		}
	}
	return names
}

// sameNames fails the test when got is not want, in order.
func sameNames(t *testing.T, got, want []string) {
	t.Helper()
	if fmt.Sprint(got) != fmt.Sprint(want) {
		t.Fatalf("got %q, want %q", got, want)
	}
}

// Each form of logic is flagged once, on the line of the function name.
func TestEachFormOfLogicIsFlaggedOnce(t *testing.T) {
	forms := []struct{ name, body string }{
		{"if", "func form(flag bool) {\n\tif flag {\n\t}\n}\n"},
		{"switch", "func form(n int) {\n\tswitch n {\n\tcase 1:\n\t}\n}\n"},
		{"type switch", "func form(v any) {\n\tswitch v.(type) {\n\tcase int:\n\t}\n}\n"},
		{"select", "func form(ch chan int) {\n\tselect {\n\tcase <-ch:\n\t}\n}\n"},
		{"for", "func form() {\n\tfor i := 0; i < 2; i++ {\n\t}\n}\n"},
		{"range", "func form(list []int) {\n\tfor range list {\n\t}\n}\n"},
		{"goto", "func form() {\n\tgoto done\ndone:\n}\n"},
	}
	for _, form := range forms {
		t.Run(form.name, func(t *testing.T) {
			got := lintIn(t, map[string]string{"form.go": "package demo\n\n" + form.body}, LintOptions{})
			sameFound(t, got, "form.go:3 CUP-I008")
		})
	}
}

func TestAFunctionWithLogicThatIsNotInAPrimitiveIsAWarning(t *testing.T) {
	got := lintIn(t, map[string]string{"who_is_due.go": `package demo

func whoIsDue(entries []string) string {
	if len(entries) == 0 {
		return "say"
	}
	return "model"
}

func pick(list []int) int {
	for _, each := range list {
		if each > 0 {
			return each
		}
	}
	return 0
}

func choose(flag bool) string {
	switch flag {
	case true:
		return "a"
	}
	return "b"
}

func wait(ch chan int) {
	select {
	case <-ch:
	}
}

func plain(a, b int) int {
	return a + b
}

func both(a, b bool) bool {
	return a && b || !a
}

func first(list []int) int {
	x := list[0]
	goto end
end:
	return x
}
`}, LintOptions{})
	sameFound(t, got,
		"who_is_due.go:3 CUP-I008",
		"who_is_due.go:10 CUP-I008",
		"who_is_due.go:19 CUP-I008",
		"who_is_due.go:27 CUP-I008",
		"who_is_due.go:41 CUP-I008")
	sameNames(t, flaggedNames(got), []string{
		"Function `whoIsDue`", "Function `pick`", "Function `choose`", "Function `wait`", "Function `first`",
	})
	want := "Function `whoIsDue` has logic and is not a Filter, a Predicate, a Tap, a Hook or a Pipeline. Write it as a primitive"
	if !strings.Contains(got.findings[0].Message, want) {
		t.Fatalf("message %q, want it to contain %q", got.findings[0].Message, want)
	}
}

func TestAMethodOfATypeThatIsNotAPrimitiveAndAVarWithLogic(t *testing.T) {
	got := lintIn(t, map[string]string{"record_store.go": `package demo

type RecordStore struct {
	files []string
}

func (s RecordStore) Read(id string) []string {
	if id == "" {
		return nil
	}
	return s.files
}

type Point struct {
	x float64
}

func (p Point) Double() float64 {
	return p.x * 2
}

func (p Point) String() string {
	switch {
	case p.x > 0:
		return "positive"
	}
	return "other"
}

var handler = func(flag bool) int {
	if flag {
		return 1
	}
	return 2
}

var limit = 20000

var second = func(flag bool) int {
	if flag {
		return 1
	}
	return 2
}
`}, LintOptions{})
	sameFound(t, got,
		"record_store.go:7 CUP-I008",
		"record_store.go:22 CUP-I008",
		"record_store.go:30 CUP-I008")
	sameNames(t, flaggedNames(got), []string{
		"Method `RecordStore.Read`", "Method `Point.String`", "Var `handler`",
	})
	want := "Method `RecordStore.Read` has logic, and `RecordStore` is not a primitive"
	if !strings.Contains(got.findings[0].Message, want) {
		t.Fatalf("message %q, want it to contain %q", got.findings[0].Message, want)
	}
}

// Logic in a primitive, and code with no logic, is not flagged.
func TestLogicInAPrimitiveAndCodeWithoutLogicHaveNoFinding(t *testing.T) {
	got := lintIn(t, map[string]string{
		"pick_filter.go": `package demo

import "context"

type PickFilter struct{ on bool }

func (f PickFilter) Call(ctx context.Context, payload any) error {
	return nil
}

func (f PickFilter) pick(value int) int {
	if value > 0 {
		return value
	}
	return 0
}
`,
		"is_on_predicate.go": `package demo

import "context"

type IsOnPredicate struct{}

func (IsOnPredicate) Test(ctx context.Context, payload any) bool {
	switch payload.(type) {
	case nil:
		return false
	}
	return true
}
`,
		"see_tap.go": `package demo

import "context"

type SeeTap struct{}

func (SeeTap) Observe(ctx context.Context, payload any) error {
	for i := 0; i < 2; i++ {
	}
	return nil
}
`,
		"log_hook.go": `package demo

import "context"

type LogHook struct{ HookBase }

func (LogHook) Before(ctx context.Context, step string, payload any) {
	if step != "" {
		return
	}
}
`,
		"main_pipeline.go": `package demo

type MainPipeline struct{}

func (MainPipeline) AddSteps(pipeline any) {
	if pipeline == nil {
		return
	}
}
`,
		"types.go": `package demo

type Due int

const (
	Say Due = iota
	Model
)

const Limit = 20000

var names = []string{"a"}

type Names []string
`,
	}, LintOptions{})
	sameFound(t, got)
}

// A helper method in a file that does not hold its type is not part of the primitive.
func TestAMethodInAnotherFileIsNotPartOfThePrimitive(t *testing.T) {
	got := lintIn(t, map[string]string{
		"pick_filter.go": "package demo\n\nimport \"context\"\n\ntype PickFilter struct{}\n\nfunc (PickFilter) Call(ctx context.Context, payload any) error {\n\treturn nil\n}\n",
		"pick_helper.go": "package demo\n\nfunc (f PickFilter) helper(value int) int {\n\tif value > 0 {\n\t\treturn 1\n\t}\n\treturn 0\n}\n",
	}, LintOptions{})
	sameFound(t, got, "pick_helper.go:3 CUP-I008")
}

// main and init are functions, so their logic is flagged.
func TestMainAndInitAreFlagged(t *testing.T) {
	got := lintIn(t, map[string]string{"main.go": `package main

func main() {
	if true {
	}
}

func init() {
	for {
		break
	}
}
`}, LintOptions{})
	sameFound(t, got, "main.go:3 CUP-I008", "main.go:8 CUP-I008")
}

// Logic in a function literal counts for the function around it.
func TestLogicInAFunctionLiteralCountsForTheFunctionAroundIt(t *testing.T) {
	got := lintIn(t, map[string]string{"literal.go": `package demo

func makeHandler(flag bool) func() int {
	return func() int {
		if flag {
			return 1
		}
		return 2
	}
}

func makeCounter() func() int {
	return func() int {
		return 1
	}
}
`}, LintOptions{})
	sameFound(t, got, "literal.go:3 CUP-I008")
}

func TestATestFileHasNoFinding(t *testing.T) {
	got := lintIn(t, map[string]string{"logic_test.go": "package demo\n\nimport \"testing\"\n\nfunc TestPick(t *testing.T) {\n\tif true {\n\t}\n}\n"}, LintOptions{})
	sameFound(t, got)
}

func TestAPickFunctionWithAMarkerAboveItIsAllowed(t *testing.T) {
	got := lintIn(t, map[string]string{"helper.go": `package demo

// Pick picks one.
//
// cup: allow-plain a pure helper of two Predicates
func pick(a bool) int {
	if a {
		return 1
	}
	return 2
}
`}, LintOptions{})
	sameFound(t, got)
	if got.suppressed != 1 || got.report != "No findings (1 suppressed)." {
		t.Fatalf("suppressed %d, report %q", got.suppressed, got.report)
	}
}

// A warning does not fail the run, unless the run is strict.
func TestAWarningDoesNotFailTheRunUnlessItIsStrict(t *testing.T) {
	files := map[string]string{"pick.go": "package demo\n\nfunc pick(a bool) int {\n\tif a {\n\t\treturn 1\n\t}\n\treturn 2\n}\n"}
	soft := lintIn(t, files, LintOptions{})
	if soft.exitCode != 0 {
		t.Fatalf("exit code %d, want 0", soft.exitCode)
	}
	if !strings.Contains(soft.report, "pick.go:3:6  CUP-I008 logic-outside-primitive  warning: Function `pick` has logic") {
		t.Fatalf("report %q", soft.report)
	}
	if !strings.HasSuffix(soft.report, "\nNo findings. 1 warning.") {
		t.Fatalf("report %q", soft.report)
	}
	strict := lintIn(t, files, LintOptions{Strict: true})
	if strict.exitCode != 1 {
		t.Fatalf("strict exit code %d, want 1", strict.exitCode)
	}
}

// A warning and a finding are counted apart.
func TestAWarningAndAFindingAreCountedApart(t *testing.T) {
	got := lintIn(t, map[string]string{
		"pick.go":   "package demo\n\nfunc pick(a bool) int {\n\tif a {\n\t\treturn 1\n\t}\n\treturn 2\n}\n",
		"broken.go": "package demo\n\nfunc (\n",
	}, LintOptions{})
	sameFound(t, got, "broken.go:3 CUP-I000", "pick.go:3 CUP-I008")
	if got.exitCode != 1 {
		t.Fatalf("exit code %d, want 1", got.exitCode)
	}
	if !strings.HasSuffix(got.report, "\n1 finding. 1 warning.") {
		t.Fatalf("report %q", got.report)
	}
}

func TestTheRuleCanBeSwitchedOff(t *testing.T) {
	got := lintIn(t, map[string]string{"helper.go": "package demo\n\nfunc pick(a bool) int {\n\tif a {\n\t\treturn 1\n\t}\n\treturn 2\n}\n"}, disable(LogicOutsidePrimitive))
	sameFound(t, got)
	if got.report != "No findings." {
		t.Fatalf("report %q", got.report)
	}
}
