package main

import (
	"path/filepath"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// rendered gives the two texts that RenderFilesFilter makes in a project with
// the given files and module, for the arguments.
func rendered(t *testing.T, files map[string]string, module string, args ...string) (component, test string) {
	t.Helper()
	root := t.TempDir()
	if module != "" {
		write(t, filepath.Join(root, "go.mod"), moduleText(module))
	}
	for path, body := range files {
		write(t, filepath.Join(root, path), body)
	}
	in := codeupipe.NewPayload(map[string]any{"root": root, "args": args,
		"module": moduleOfGoMod(moduleText(module))})
	if _, refusal := runStep(ParseArgumentsFilter{}, in); refusal != nil {
		t.Fatalf("the first step refused: %s", refusal.Message)
	}
	if _, refusal := runStep(TypeNameFilter{}, in); refusal != nil {
		t.Fatalf("the second step refused: %s", refusal.Message)
	}
	out, refusal := runStep(PlanFilesFilter{}, in)
	if refusal != nil {
		t.Fatalf("the third step refused: %s", refusal.Message)
	}
	out, refusal = runStep(RenderFilesFilter{}, out)
	if refusal != nil {
		t.Fatalf("the fourth step refused: %s", refusal.Message)
	}
	return text(out, "component_text"), text(out, "test_text")
}

func TestEachKindDoesNothingAndHasItsHeader(t *testing.T) {
	for _, want := range [][3]string{
		{"filter", "DiscountFilter", "func (DiscountFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {"},
		{"predicate", "AtLeastPredicate", "func (AtLeastPredicate) Test(ctx context.Context, payload *codeupipe.Payload) bool {"},
		{"tap", "AuditTap", "func (AuditTap) Observe(ctx context.Context, payload *codeupipe.Payload) error {"},
		{"hook", "PrintStepsHook", "func (PrintStepsHook) Before(ctx context.Context, step string, payload *codeupipe.Payload) {"},
		{"pipeline", "PricingPipeline", "func (PricingPipeline) AddSteps(pipeline *codeupipe.Pipeline) {"},
	} {
		component, _ := rendered(t, nil, "pricing", want[0], want[1])
		same(t, stringsIn(component, "// "+want[1]+": TODO: say what "+want[1]+" does."), true)
		same(t, stringsIn(component, want[2]), true)
		same(t, stringsIn(component, "type "+want[1]+" struct"), true)
	}
}

func TestTheTestFailsWithTheKnownMessage(t *testing.T) {
	_, test := rendered(t, nil, moduleText("pricing"), "filter", "Discount")
	same(t, stringsIn(test, `t.Fatal("Write the acceptance case for DiscountFilter.")`), true)
	same(t, stringsIn(test, "func TestDiscountFilter(t *testing.T)"), true)
}

func TestTheTestOfADirectoryIsBesideItsComponent(t *testing.T) {
	_, test := rendered(t, nil, "pricing", "filter", "Discount", "src/pricing")
	// Go keeps the test beside its source, in the package of the component, so
	// the test needs no import: a package cannot import itself.
	same(t, stringsIn(test, `"pricing/src/pricing/discount_filter"`), false)
	same(t, stringsIn(test, "package pricing"), true)
}

func TestWithoutAModuleTheTestNeedsNoImport(t *testing.T) {
	_, test := rendered(t, nil, "", "filter", "Discount")
	same(t, stringsIn(test, "import"), true)
	same(t, stringsIn(test, "codeupipe"), false)
}

func TestModuleOfGoMod(t *testing.T) {
	same(t, moduleOfGoMod("module pricing\n\ngo 1.22\n"), "pricing")
	same(t, moduleOfGoMod("module \"pricing\"\n"), "pricing")
	same(t, moduleOfGoMod("\tmodule example.com/a/b\n"), "example.com/a/b")
	same(t, moduleOfGoMod("go 1.22\n"), "")
}

func TestFillReplacesEachKey(t *testing.T) {
	same(t, fill("a {x} b {x} c", map[string]string{"x": "1"}), "a 1 b 1 c")
}
