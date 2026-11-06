package codeupipelint

import (
	"go/parser"
	"go/token"
	"strings"
	"testing"
)

// The Rust test of CUP-I005, in Go. The Filter and the Tap share a file,
// so the Tap is flagged. A helper type and a local type are not.
func TestOnePrimitivePerFileFlagsEachPrimitiveAfterTheFirst(t *testing.T) {
	setFilter := `package demo

import "context"

type SetFilter struct{}

func (SetFilter) Call(ctx context.Context, run *LintRun) error { return nil }

type Helper struct{}

type SeeTap struct{}

func (SeeTap) Observe(ctx context.Context, run *LintRun) error { return nil }

func make() {
	type LocalFilter struct{}
}
`
	// A file in a _test.go file is not checked, as the Rust tests/ folder.
	two := `package demo

import "context"

type AFilter struct{}

func (AFilter) Call(ctx context.Context, run *LintRun) error { return nil }

type BFilter struct{}

func (BFilter) Call(ctx context.Context, run *LintRun) error { return nil }
`
	got := lintIn(t, map[string]string{"set_filter.go": setFilter, "steps_test.go": two}, LintOptions{})
	sameFound(t, got, "set_filter.go:11 CUP-I005", "set_filter.go:11 CUP-I006")
	if !strings.HasPrefix(got.findings[0].Message, "Tap `SeeTap` shares this file with Filter `SetFilter`.") {
		t.Fatalf("message %q", got.findings[0].Message)
	}
}

// A Hook is a primitive only because it embeds codeupipe.HookBase. It
// shares the file with the Filter, so it is flagged.
func TestOnePrimitivePerFileCountsAHookThatEmbedsHookBase(t *testing.T) {
	text := `package demo

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

type DiscountFilter struct{}

func (DiscountFilter) Call(ctx context.Context, run *LintRun) error { return nil }

type AuditHook struct{ codeupipe.HookBase }
`
	got := lintIn(t, map[string]string{"discount_filter.go": text}, LintOptions{})
	sameFound(t, got, "discount_filter.go:13 CUP-I005", "discount_filter.go:13 CUP-I006")
	if !strings.HasPrefix(got.findings[0].Message, "Hook `AuditHook` shares this file with Filter `DiscountFilter`.") {
		t.Fatalf("message %q", got.findings[0].Message)
	}
}

// A named pipeline (a type with AddSteps) is a primitive. It shares the
// file with the Filter, so it is flagged.
func TestOnePrimitivePerFileCountsANamedPipeline(t *testing.T) {
	text := `package demo

type DiscountFilter struct{}

func (DiscountFilter) Call(ctx context.Context, run *LintRun) error { return nil }

type PricingPipeline struct{}

func (PricingPipeline) AddSteps(pipeline *codeupipe.Pipeline) {}
`
	got := lintIn(t, map[string]string{"discount_filter.go": text}, LintOptions{})
	sameFound(t, got, "discount_filter.go:7 CUP-I005", "discount_filter.go:7 CUP-I006")
	if !strings.HasPrefix(got.findings[0].Message, "Pipeline `PricingPipeline` shares this file with Filter `DiscountFilter`.") {
		t.Fatalf("message %q", got.findings[0].Message)
	}
}

// The marker "cup: allow-shared-file" alone above the type allows the
// finding below it, on that line only.
func TestOnePrimitivePerFileIsAllowedByTheSharedFileMarker(t *testing.T) {
	text := `package demo

import "context"

type SetFilter struct{}

func (SetFilter) Call(ctx context.Context, run *LintRun) error { return nil }

// cup: allow-shared-file the two steps live together on purpose
type SeeTap struct{}

func (SeeTap) Observe(ctx context.Context, run *LintRun) error { return nil }
`
	got := lintIn(t, map[string]string{"set_filter.go": text}, LintOptions{})
	sameFound(t, got)
	if got.suppressed != 2 {
		t.Fatalf("suppressed %d findings, want 2 (CUP-I005 and CUP-I006)", got.suppressed)
	}
}

// A file that has only one primitive gives no CUP-I005 finding, even when
// it has plain types and functions beside it.
func TestOnePrimitivePerFileIgnoresPlainTypesAndFunctions(t *testing.T) {
	text := `package demo

import "context"

type Config struct{ Name string }

func helper() int { return 1 }

type DiscountFilter struct{}

func (DiscountFilter) Call(ctx context.Context, run *LintRun) error { return nil }
`
	got := lintIn(t, map[string]string{"discount_filter.go": text}, LintOptions{})
	sameFound(t, got)
}

// A type can have methods in two files. Each file sees only its own
// methods: the Filter's file sees a Filter, and the other file sees a
// Predicate for the same type name.
func TestPrimitivesInSeesOnlyTheMethodsOfItsOwnFile(t *testing.T) {
	filter := "package demo\n\nimport \"context\"\n\ntype DiscountFilter struct{}\n\nfunc (DiscountFilter) Call(ctx context.Context, run *LintRun) error { return nil }\n"
	check := "package demo\n\nimport \"context\"\n\nfunc (DiscountFilter) Test(ctx context.Context, run *LintRun) bool { return true }\n"
	if got := primitiveKinds(t, filter); got != "DiscountFilter:Filter" {
		t.Fatalf("filter file gives %q", got)
	}
	if got := primitiveKinds(t, check); got != "DiscountFilter:Predicate" {
		t.Fatalf("check file gives %q", got)
	}
}

// primitiveKinds parses text and gives "Name:Kind" of each primitive, joined
// by a space.
func primitiveKinds(t *testing.T, text string) string {
	t.Helper()
	file, err := parser.ParseFile(token.NewFileSet(), "x.go", text, parser.ParseComments)
	if err != nil {
		t.Fatal(err)
	}
	var kinds []string
	for _, primitive := range PrimitivesIn(file) {
		kinds = append(kinds, primitive.Name+":"+primitive.Kind.Name())
	}
	return strings.Join(kinds, " ")
}
