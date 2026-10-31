package main

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// pricingLayout is the layout of most of the tests of phase 2.
const pricingLayout = `lang: go
root: src/pricing
components:
  - {kind: filter, name: Discount, description: "Takes a rate off the price."}
  - {kind: predicate, name: AtLeast}
  - {kind: filter, name: MarkBulk}
  - {kind: hook, name: PrintSteps}
  - {kind: pipeline, name: Clean, steps: [Discount]}
  - kind: pipeline
    name: Pricing
    steps: [CleanPipeline, {valve: [AtLeast, MarkBulk]}]
    hooks: [PrintSteps]
`

// runLayoutIn runs the Layout pipeline in a project with the layout text in
// cup.layout.yaml, and gives the output or the Refusal.
func runLayoutIn(t *testing.T, root, layoutText string) (*codeupipe.Payload, *Refusal) {
	t.Helper()
	write(t, filepath.Join(root, "cup.layout.yaml"), layoutText)
	out, err := codeupipe.NewNamedPipeline(Layout{}).Run(context.Background(), codeupipe.NewPayload(map[string]any{
		"root": root, "args": []string{"--layout", "cup.layout.yaml"}}))
	var refusal *Refusal
	if errors.As(err, &refusal) {
		return nil, refusal
	}
	if err != nil {
		t.Fatal(err)
	}
	return out, nil
}

func TestLayoutMakesEachComponentAndItsSteps(t *testing.T) {
	root := t.TempDir()
	out, refusal := runLayoutIn(t, root, pricingLayout)
	if refusal != nil {
		t.Fatal(refusal.Message)
	}
	written, _ := out.Get("written").([]string)
	same(t, len(written), 12)
	same(t, written[0], "src/pricing/discount_filter.go")
	same(t, written[1], "src/pricing/discount_filter_test.go")
	pipeline, err := os.ReadFile(filepath.Join(root, "src/pricing/pricing_pipeline.go"))
	if err != nil {
		t.Fatal(err)
	}
	for _, line := range []string{
		"package pricing",
		"\tpipeline.AddPipeline(codeupipe.NewNamedPipeline(CleanPipeline{}))",
		"\tpipeline.AddValve(AtLeastPredicate{}, MarkBulkFilter{})",
		"\tpipeline.UseHook(PrintStepsHook{})",
	} {
		if !strings.Contains(string(pipeline), line) {
			t.Fatalf("%q is not in\n%s", line, pipeline)
		}
	}
}

func TestLayoutKeepsEachFileAndNamesAPipelineWhoseStepsChanged(t *testing.T) {
	root := t.TempDir()
	runLayoutIn(t, root, pricingLayout)
	again, _ := runLayoutIn(t, root, pricingLayout)
	kept, _ := again.Get("kept").([]string)
	same(t, len(kept), 12)
	same(t, again.Get("stale"), []string{})
	grown, _ := runLayoutIn(t, root, strings.Replace(pricingLayout, "steps: [Discount]", "steps: [Discount, MarkBulk]", 1))
	same(t, grown.Get("stale"), []string{"src/pricing/clean_pipeline.go"})
}

func TestLayoutReadsJSON(t *testing.T) {
	out, refusal := runLayoutIn(t, t.TempDir(), `{"lang": "go", "components": [{"kind": "tap", "name": "Audit"}]}`)
	if refusal != nil {
		t.Fatal(refusal.Message)
	}
	same(t, out.Get("written"), []string{"audit_tap.go", "audit_tap_test.go"})
}

func TestLayoutRefusesTheWholeLayoutForEachRule(t *testing.T) {
	base := "lang: go\nroot: src/pricing\ncomponents:\n"
	discount := "  - {kind: filter, name: Discount}\n"
	for _, c := range []struct{ text, wanted string }{
		{"- lang: go\n", "is not a mapping"},
		{base + "  - kind: filter\n    name: A\n    name: B\n", "line 6 has the key name two times"},
		{"lang: rust\ncomponents:\n" + discount, "is for rust, and this is codeupipe add for go"},
		{"components:\n" + discount, "has no lang:"},
		{base + "  - {kind: filter, name: Discount, step: []}\n", "Unknown key step in the component Discount"},
		{base + "  - {kind: filter, name: Discount, steps: []}\n", "steps: is only for a pipeline"},
		{base + "  - {kind: pipeline, name: P, steps: [{valve: [A]}]}\n", "The step map[valve:[A]] of P cannot be read"},
		{base + discount + "  - {kind: filter, name: DiscountFilter}\n", "Two components are DiscountFilter"},
		{base + "  - {kind: pipeline, name: P, steps: [Tax]}\n", "Tax, a step of P, is not a component"},
		{base + "  - {kind: predicate, name: AtLeast}\n  - {kind: pipeline, name: P, steps: [AtLeast]}\n", "A predicate is not a step"},
		{base + discount + "  - {kind: pipeline, name: P, hooks: [Discount]}\n", "Discount in the hooks of P is a filter, not a hook"},
		{base + "  - {kind: pipeline, name: Outer, steps: [Inner]}\n  - {kind: pipeline, name: Inner, steps: [Outer]}\n",
			"OuterPipeline -> InnerPipeline -> OuterPipeline"},
		{base + "  - {kind: valve, name: Bulk}\n", "add_valve(predicate, filter)"},
	} {
		root := t.TempDir()
		_, refusal := runLayoutIn(t, root, c.text)
		if refusal == nil || refusal.ExitCode != 2 || !strings.Contains(refusal.Message, c.wanted) {
			t.Fatalf("%q: got %#v, want exit 2 with %q", c.text, refusal, c.wanted)
		}
		if _, err := os.Stat(filepath.Join(root, "src")); err == nil {
			t.Fatalf("%q: a refused layout wrote a file", c.text)
		}
	}
}

func TestLayoutTakesNothingElse(t *testing.T) {
	for _, args := range [][]string{{"filter", "--layout", "x.yaml"}, {"--layout", "x.yaml", "--description", "d"}} {
		err := (ParseLayoutArgumentsFilter{}).Call(context.Background(), codeupipe.NewPayload(map[string]any{"args": args}))
		var refusal *Refusal
		if !errors.As(err, &refusal) || !strings.Contains(refusal.Message, "--layout takes no") {
			t.Fatalf("%v: got %v", args, err)
		}
	}
	same(t, usesLayout([]string{"--layout=x.yaml"}), true)
	same(t, usesLayout([]string{"filter", "Discount"}), false)
}

func TestStepsOfLeavesOutTheArgumentsAndTheComments(t *testing.T) {
	layout := "\tpipeline.AddFilter(DiscountFilter{})\n\tpipeline.AddTap(AuditTap{})\n"
	same(t, stepsOf("// a note\n\tpipeline.AddFilter(&DiscountFilter{Rate: 0.1})\n\tpipeline.AddTap(AuditTap{ /* log */ })\n"),
		stepsOf(layout))
	if deepEqual(stepsOf("\tpipeline.AddTap(AuditTap{})\n\tpipeline.AddFilter(DiscountFilter{})\n"), stepsOf(layout)) {
		t.Fatal("two steps in the other order are the same steps")
	}
}
