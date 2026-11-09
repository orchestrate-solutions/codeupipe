package main

import (
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// named gives the type name and the file name that TypeNameFilter makes from
// a kind and a name, or the exit code and the message of a refusal.
func named(t *testing.T, kind, name string) (typeName, snake string, code int, stderr string) {
	t.Helper()
	out, refusal := runStep(TypeNameFilter{}, codeupipe.NewPayload(map[string]any{"kind": kind, "name": name}))
	if refusal != nil {
		return "", "", refusal.ExitCode, refusal.Message
	}
	return text(out, "type_name"), text(out, "snake"), 0, ""
}

func TestTheTypeNameHasItsRoleAndTheFileNameTheRuleOfTheLinters(t *testing.T) {
	for _, want := range [][3]string{
		{"filter", "Discount", "DiscountFilter"},
		{"filter", "DiscountFilter", "DiscountFilter"},
		{"predicate", "at_least", "AtLeastPredicate"},
		{"tap", "audit-log", "AuditLogTap"},
		{"filter", "HTTPGet", "HTTPGetFilter"},
		{"hook", "printSteps", "PrintStepsHook"},
		{"pipeline", "Pricing", "PricingPipeline"},
	} {
		typeName, snake, code, stderr := named(t, want[0], want[1])
		same(t, code, 0)
		same(t, stderr, "")
		same(t, typeName, want[2])
		same(t, snake, snakeCase(want[2]))
	}
}

func TestTheFileNamesOfTheRule(t *testing.T) {
	for _, want := range [][2]string{
		{"DiscountFilter", "discount_filter"},
		{"HTTPGetFilter", "http_get_filter"},
		{"IOUriFilter", "io_uri_filter"},
		{"AtLeastPredicate", "at_least_predicate"},
		{"AuditLogTap", "audit_log_tap"},
		{"PrintStepsHook", "print_steps_hook"},
		{"PricingPipeline", "pricing_pipeline"},
	} {
		same(t, snakeCase(want[0]), want[1])
	}
}

func TestAKindOrANameThatCannotBeUsedIsRefusedWithExit2(t *testing.T) {
	for _, want := range [][3]string{
		{"valve", "AtLeast", "add_valve(predicate, filter)"},
		{"payload", "Order", "runtime"},
		{"state", "Run", "runtime"},
		{"widget", "Thing", "filter, predicate, tap, hook, pipeline"},
		{"filter", "2Fast", "2Fast"},
		{"filter", "Take Rate", "Take Rate"},
		{"filter", "", "name"},
	} {
		_, _, code, stderr := named(t, want[0], want[1])
		same(t, code, 2)
		same(t, stringsIn(stderr, want[2]), true)
	}
}
