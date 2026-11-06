package codeupipelint

import (
	"strings"
	"testing"
)

// The Rust tests of CUP-I006 and CUP-I007, in Go. Each primitive gets its
// role finding first, then its file name finding. A type with the wrong
// shape for a method is not a primitive.
func TestPrimitiveNamesFlagARoleAndAFileNameThatDoNotFit(t *testing.T) {
	got := lintIn(t, map[string]string{
		"discount.go":    "package demo\n\ntype Discount struct{}\n\nfunc (Discount) Call(ctx context.Context, run *LintRun) error { return nil }\n",
		"audit.go":       "package demo\n\ntype Audit struct{}\n\nfunc (Audit) Observe(ctx context.Context, run *LintRun) error { return nil }\n",
		"at_least.go":    "package demo\n\ntype AtLeast struct{}\n\nfunc (AtLeast) Test(ctx context.Context, run *LintRun) bool { return true }\n",
		"print_steps.go": "package demo\n\ntype PrintSteps struct{ codeupipe.HookBase }\n",
		"pricing.go":     "package demo\n\ntype Pricing struct{}\n\nfunc (Pricing) AddSteps(pipeline *codeupipe.Pipeline) {}\n",
		"point.go":       "package demo\n\ntype Point struct{}\n\nfunc (Point) Call(a, b int) {}\n\nfunc (Point) Test() {}\n",
	}, LintOptions{})
	sameFound(t, got,
		"at_least.go:3 CUP-I006", "at_least.go:3 CUP-I007",
		"audit.go:3 CUP-I006", "audit.go:3 CUP-I007",
		"discount.go:3 CUP-I006", "discount.go:3 CUP-I007",
		"pricing.go:3 CUP-I006", "pricing.go:3 CUP-I007",
		"print_steps.go:3 CUP-I006", "print_steps.go:3 CUP-I007",
	)
	if !strings.HasPrefix(got.findings[1].Message, "Predicate `AtLeast` does not say what it is. Name it `AtLeastPredicate`.") {
		t.Fatalf("message %q", got.findings[1].Message)
	}
	if !strings.HasPrefix(got.findings[2].Message, "`AuditTap` is in `audit.go`. Put it in `audit_tap.go`.") {
		t.Fatalf("message %q", got.findings[2].Message)
	}
}

// Primitives whose names and file names fit give no finding: a Filter, a
// Tap, a named Pipeline, a Hook that embeds HookBase, and an unexported and
// a generic Filter.
func TestPrimitiveNamesAcceptsNamesThatFit(t *testing.T) {
	got := lintIn(t, map[string]string{
		"discount_filter.go":  "package demo\n\ntype DiscountFilter struct{}\n\nfunc (DiscountFilter) Call(ctx context.Context, run *LintRun) error { return nil }\n",
		"lower_filter.go":     "package demo\n\ntype lowerFilter struct{}\n\nfunc (lowerFilter) Call(ctx context.Context, run *LintRun) error { return nil }\n",
		"order_filter.go":     "package demo\n\ntype OrderFilter[P any] struct{}\n\nfunc (f *OrderFilter[P]) Call(ctx context.Context, payload P) error { return nil }\n",
		"audit_tap.go":        "package demo\n\ntype AuditTap struct{}\n\nfunc (AuditTap) Observe(ctx context.Context, run *LintRun) error { return nil }\n",
		"print_steps_hook.go": "package demo\n\ntype PrintStepsHook struct{ codeupipe.HookBase }\n",
		"pricing_pipeline.go": "package demo\n\ntype PricingPipeline struct{}\n\nfunc (PricingPipeline) AddSteps(pipeline *codeupipe.Pipeline) {}\n",
	}, LintOptions{})
	sameFound(t, got)
}

// A Hook that is a primitive only because it embeds codeupipe.HookBase is
// checked like any other primitive.
func TestPrimitiveNamesChecksAHookThatEmbedsHookBase(t *testing.T) {
	got := lintIn(t, map[string]string{
		"print_steps.go": "package demo\n\ntype PrintSteps struct{ codeupipe.HookBase }\n",
	}, LintOptions{})
	sameFound(t, got, "print_steps.go:3 CUP-I006", "print_steps.go:3 CUP-I007")
	if !strings.HasPrefix(got.findings[1].Message, "Hook `PrintSteps` does not say what it is. Name it `PrintStepsHook`.") {
		t.Fatalf("message %q", got.findings[1].Message)
	}
}

// A named pipeline (a type with AddSteps) whose name lacks Pipeline is
// flagged, as the Rust linter flags Pricing.
func TestPrimitiveNamesChecksANamedPipeline(t *testing.T) {
	got := lintIn(t, map[string]string{
		"pricing.go": "package demo\n\ntype Pricing struct{}\n\nfunc (Pricing) AddSteps(pipeline *codeupipe.Pipeline) {}\n",
	}, LintOptions{})
	sameFound(t, got, "pricing.go:3 CUP-I006", "pricing.go:3 CUP-I007")
}

// A _test.go file is not checked for names.
func TestPrimitiveNamesSkipsATestFile(t *testing.T) {
	got := lintIn(t, map[string]string{
		"discount_test.go": "package demo\n\ntype Discount struct{}\n\nfunc (Discount) Call(ctx context.Context, run *LintRun) error { return nil }\n",
	}, LintOptions{})
	sameFound(t, got)
}

// The marker "cup: allow-name" alone above the type allows both findings.
func TestPrimitiveNamesIsAllowedByTheNameMarker(t *testing.T) {
	got := lintIn(t, map[string]string{
		"discount.go": "package demo\n\n// cup: allow-name the name comes from the paper\ntype Discount struct{}\n\nfunc (Discount) Call(ctx context.Context, run *LintRun) error { return nil }\n",
	}, LintOptions{})
	sameFound(t, got)
	if got.suppressed != 2 {
		t.Fatalf("suppressed %d findings, want 2 (CUP-I006 and CUP-I007)", got.suppressed)
	}
}

// The snake case of a type name is its file name, without ".go".
func TestSnakeCaseOfAPrimitiveName(t *testing.T) {
	cases := map[string]string{
		"DiscountFilter":   "discount_filter",
		"HTTPGetFilter":    "http_get_filter",
		"ParseJSONFilter":  "parse_json_filter",
		"ParseHTMLFilter":  "parse_html_filter",
		"V2Filter":         "v2_filter",
		"discountFilter":   "discount_filter",
		"Filter":           "filter",
		"AtLeastPredicate": "at_least_predicate",
		"PricingPipeline":  "pricing_pipeline",
	}
	filter := AnalyzePrimitiveNamesFilter{}
	for name, want := range cases {
		if got := filter.snakeCase(name); got != want {
			t.Errorf("snakeCase(%q) = %q, want %q", name, got, want)
		}
	}
}
