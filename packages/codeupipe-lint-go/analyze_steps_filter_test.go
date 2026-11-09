package codeupipelint

import (
	"fmt"
	"strings"
	"testing"
)

// stepsIn lints a Go file, "build.go", whose text is a package clause and
// body. A line with "// want CUP-..." must have that finding, and no other
// line may have one.
func stepsIn(t *testing.T, body string) linted {
	t.Helper()
	return stepsInFile(t, "build.go", body)
}

// stepsInFile is stepsIn for a file with the name file.
func stepsInFile(t *testing.T, file, body string) linted {
	t.Helper()
	text := "package demo\n\n" + body
	got := lintIn(t, map[string]string{file: text}, disable("CUP-I003", "CUP-I004", "CUP-I005", "CUP-I006", "CUP-I007", "CUP-I008"))
	sameFound(t, got, wanted(file, text)...)
	return got
}

// wanted gives "file:line RULE" for each line of text that ends with
// "// want RULE".
func wanted(file, text string) []string {
	var out []string
	for index, line := range strings.Split(text, "\n") {
		at := strings.LastIndex(line, "// want ")
		if at < 0 {
			continue
		}
		out = append(out, fmt.Sprintf("%s:%d %s", file, index+1, strings.TrimSpace(line[at+len("// want "):])))
	}
	return out
}

func TestStepsNamedTypesAtTopLevelAreClean(t *testing.T) {
	got := stepsIn(t, `type MarkFilter struct{}

type IsOnPredicate struct{}

type InnerPipeline struct{}

func build(pipeline *Pipeline) {
	pipeline.AddFilter(MarkFilter{})
	pipeline.AddFilter(&MarkFilter{})
	pipeline.AddFilter((MarkFilter{}))
	pipeline.AddValve(IsOnPredicate{}, MarkFilter{})
	kept := MarkFilter{}
	pipeline.AddFilter(kept)
	pipeline.AddTap(audit.AuditTap{})
	pipeline.AddPipeline(codeupipe.NewNamedPipeline(InnerPipeline{}))
}
`)
	if got.exitCode != 0 {
		t.Fatalf("exit code %d, want 0\n%s", got.exitCode, got.report)
	}
}

func TestStepsLocalTypeIsA003(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	type localFilter struct{}
	type localTap struct{}
	type localPipeline struct{}
	pipeline.AddFilter(localFilter{}) // want CUP-A003
	pipeline.AddFilter(&localFilter{}) // want CUP-A003
	pipeline.AddFilter((localFilter{})) // want CUP-A003
	pipeline.AddValve(IsOnPredicate{}, localFilter{}) // want CUP-A003
	pipeline.AddTap(localTap{}) // want CUP-A003
	pipeline.AddPipeline(localPipeline{}) // want CUP-A003
}
`)
}

func TestStepsAnonymousStructIsA003(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	pipeline.AddFilter(struct{ codeupipe.HookBase }{}) // want CUP-A003
}
`)
}

func TestStepsLocalTypeFollowedNameIsA003(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	type localFilter struct{}
	kept := localFilter{}
	pipeline.AddFilter(kept) // want CUP-A003
	var declared = localFilter{}
	pipeline.AddFilter(declared) // want CUP-A003
	chained := kept
	pipeline.AddFilter(chained) // want CUP-A003
}
`)
}

func TestStepsLastAssignmentBeforeTheCallIsFollowed(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	type localFilter struct{}
	kept := localFilter{}
	kept = MarkFilter{}
	pipeline.AddFilter(kept)
	again := MarkFilter{}
	again = localFilter{}
	pipeline.AddFilter(again) // want CUP-A003
	pipeline.AddFilter(kept)
}
`)
}

func TestStepsLocalTypeIsNotSeenInAnotherFunction(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	type localFilter struct{}
	pipeline.AddFilter(localFilter{}) // want CUP-A003
	register := func() {
		pipeline.AddFilter(localFilter{}) // want CUP-A003
	}
	_ = register
}

func other(pipeline *Pipeline) {
	pipeline.AddFilter(localFilter{})
}
`)
}

func TestStepsPlainPipelineIsA005(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	pipeline.AddPipeline(codeupipe.NewPipeline()) // want CUP-A005
	pipeline.AddPipeline(cup.NewPipeline()) // want CUP-A005
	pipeline.AddPipeline(codeupipe.NewPipelineOf[*LintRun]()) // want CUP-A005
	pipeline.AddPipeline(NewPipeline()) // want CUP-A005
}
`)
}

func TestStepsPlainPipelineFollowedNameIsA005(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	inner := codeupipe.NewPipeline()
	pipeline.AddPipeline(inner) // want CUP-A005
	named := codeupipe.NewNamedPipeline(InnerPipeline{})
	pipeline.AddPipeline(named)
}
`)
}

func TestStepsNamedPipelineIsNotA005(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	pipeline.AddPipeline(codeupipe.NewNamedPipeline(InnerPipeline{}))
	pipeline.AddPipeline(codeupipe.NewNamedPipelineOf[*LintRun](InnerPipeline{}))
}
`)
}

func TestStepsPlainPipelineOutsideAddPipelineIsClean(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	pipeline.AddFilter(codeupipe.NewPipeline())
}
`)
}

func TestStepsAddStepsOfANamedPipelineIsChecked(t *testing.T) {
	stepsIn(t, `type PricingPipeline struct{}

func (PricingPipeline) AddSteps(pipeline *Pipeline) {
	pipeline.AddPipeline(codeupipe.NewPipeline()) // want CUP-A005
}
`)
}

func TestStepsFunctionTypeIsA001(t *testing.T) {
	stepsIn(t, `type FilterFunc func(payload *Payload) error

func build(pipeline *Pipeline, fn func(*Payload) error) {
	type localFunc func()
	pipeline.AddFilter(FilterFunc(fn)) // want CUP-A001
	pipeline.AddTap(FilterFunc(fn)) // want CUP-A001
	pipeline.AddPipeline(FilterFunc(fn)) // want CUP-A001
	pipeline.AddValve(IsOnPredicate{}, FilterFunc(fn)) // want CUP-A001
	pipeline.AddFilter(localFunc(fn)) // want CUP-A001
}
`)
}

func TestStepsFunctionTypeInPredicatePlaceIsA008(t *testing.T) {
	stepsIn(t, `type PredicateFunc func(payload *Payload) bool

func build(pipeline *Pipeline, fn func(*Payload) bool) {
	pipeline.AddValve(PredicateFunc(fn), MarkFilter{}) // want CUP-A008
	predicate := PredicateFunc(fn)
	pipeline.AddValve(predicate, MarkFilter{}) // want CUP-A008
	pipeline.AddValve(MarkPredicate{}, PredicateFunc(fn)) // want CUP-A001
}
`)
}

func TestStepsConversionToATypeThatIsNotAFunctionIsClean(t *testing.T) {
	stepsIn(t, `type Count int

func build(pipeline *Pipeline) {
	pipeline.AddFilter(Count(1))
}
`)
}

func TestStepsParameterIsNotFollowed(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline, parameter *Pipeline) {
	pipeline.AddPipeline(parameter)
}
`)
}

func TestStepsNameFromAnotherFunctionIsNotFollowed(t *testing.T) {
	stepsIn(t, `func helper() {
	inner := codeupipe.NewPipeline()
	_ = inner
}

func other(pipeline *Pipeline) {
	pipeline.AddPipeline(inner)
}
`)
}

func TestStepsNameFromAnOuterFunctionIsNotFollowedInAClosure(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	inner := codeupipe.NewPipeline()
	outer := func() {
		pipeline.AddPipeline(inner)
	}
	_ = outer
}
`)
}

func TestStepsResultOfACallIsNotFollowed(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline) {
	inner := makePipeline()
	pipeline.AddPipeline(inner)
	fresh := codeupipe.NewNamedPipeline(InnerPipeline{})
	pipeline.AddPipeline(fresh)
}
`)
}

func TestStepsRangeVariableHidesTheNameInItsLoop(t *testing.T) {
	stepsIn(t, `func build(pipeline *Pipeline, list []*Pipeline) {
	inner := codeupipe.NewPipeline()
	for inner := range list {
		pipeline.AddPipeline(inner)
	}
	pipeline.AddPipeline(inner) // want CUP-A005
}
`)
}

func TestStepsMarkerOnTheLineOfTheCallAllowsAStepOnAnotherLine(t *testing.T) {
	got := stepsIn(t, `func build(pipeline *Pipeline) {
	type localFilter struct{}
	pipeline.AddFilter( // cup: allow-anonymous
		localFilter{},
	)
}
`)
	if got.suppressed != 1 {
		t.Fatalf("suppressed %d, want 1", got.suppressed)
	}
}

func TestStepsMarkersAllowTheFindingOnItsLineTheLineAboveAndTheLineOfTheCall(t *testing.T) {
	got := stepsIn(t, `func build(pipeline *Pipeline) {
	type localFilter struct{}
	pipeline.AddPipeline(codeupipe.NewPipeline()) // cup: allow-anonymous a test of the refusal
	// cup: allow-anonymous
	pipeline.AddPipeline(codeupipe.NewPipeline())
	pipeline.AddValve( // cup: allow-anonymous
		IsOnPredicate{},
		localFilter{},
	)
	pipeline.AddPipeline(codeupipe.NewPipeline()) // want CUP-A005
}
`)
	if got.suppressed != 3 {
		t.Fatalf("suppressed %d, want 3", got.suppressed)
	}
}

func TestStepsTestFilesAreChecked(t *testing.T) {
	stepsInFile(t, "flow_test.go", `func TestFlow(t *testing.T) {
	type localFilter struct{}
	pipeline.AddFilter(localFilter{}) // want CUP-A003
}
`)
}

func TestStepsMessagesNameTheStep(t *testing.T) {
	got := stepsIn(t, `type PredicateFunc func(payload *Payload) bool

func build(pipeline *Pipeline, fn func(*Payload) bool) {
	type localFilter struct{}
	kept := localFilter{}
	pipeline.AddFilter(localFilter{}) // want CUP-A003
	pipeline.AddFilter(kept) // want CUP-A003
	pipeline.AddPipeline(codeupipe.NewPipeline()) // want CUP-A005
	pipeline.AddValve(PredicateFunc(fn), MarkFilter{}) // want CUP-A008
}
`)
	want := []string{
		"Step `localFilter{}` is of a type that is declared in a function. Declare it",
		"Step `kept` is of a type that is declared in a function. Declare it",
		"Step `codeupipe.NewPipeline()` is a plain Pipeline, nested as a step. A nested pipeline must be",
		"Predicate `PredicateFunc(fn)` is a function type. A Valve predicate is",
	}
	if len(got.findings) != len(want) {
		t.Fatalf("%d findings, want %d", len(got.findings), len(want))
	}
	for index, prefix := range want {
		if !strings.HasPrefix(got.findings[index].Message, prefix) {
			t.Fatalf("message %q, want prefix %q", got.findings[index].Message, prefix)
		}
	}
}
