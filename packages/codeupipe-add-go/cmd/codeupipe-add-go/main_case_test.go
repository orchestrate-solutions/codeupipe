//go:build ignore

package main

import (
	"testing"
)

// The tests of the command from the outside: what it prints, and the files
// that it made, case by case as the contract has them (conformance/add/cases.json).

func TestAFilterGetsItsSuffix(t *testing.T) {
	got := add(t, "filter", "Discount")
	same(t, got.Exit, 0)
	same(t, got.Written, []string{"discount_filter.go", "discount_filter_test.go"})
	same(t, foundIn(t, got, "discount_filter.go", "type DiscountFilter struct{}"), true)
}

func TestANameWithItsSuffixKeepsIt(t *testing.T) {
	got := add(t, "filter", "DiscountFilter")
	same(t, got.Exit, 0)
	same(t, got.Written, []string{"discount_filter.go", "discount_filter_test.go"})
	same(t, foundIn(t, got, "discount_filter.go", "type DiscountFilter struct{}"), true)
}

func TestASnakeCaseNameBecomesPascalCase(t *testing.T) {
	got := add(t, "predicate", "at_least")
	same(t, got.Exit, 0)
	same(t, got.Written, []string{"at_least_predicate.go", "at_least_predicate_test.go"})
	same(t, foundIn(t, got, "at_least_predicate.go", "type AtLeastPredicate struct{}"), true)
}

func TestAKebabCaseNameBecomesPascalCase(t *testing.T) {
	got := add(t, "tap", "audit-log")
	same(t, got.Exit, 0)
	same(t, got.Written, []string{"audit_log_tap.go", "audit_log_tap_test.go"})
	same(t, foundIn(t, got, "audit_log_tap.go", "type AuditLogTap struct{}"), true)
}

func TestCapitalsTogetherAreOneWord(t *testing.T) {
	got := add(t, "filter", "HTTPGet")
	same(t, got.Exit, 0)
	same(t, got.Written, []string{"http_get_filter.go", "http_get_filter_test.go"})
	same(t, foundIn(t, got, "http_get_filter.go", "type HTTPGetFilter struct{}"), true)
}

func TestAHook(t *testing.T) {
	got := add(t, "hook", "PrintSteps")
	same(t, got.Exit, 0)
	same(t, got.Written, []string{"print_steps_hook.go", "print_steps_hook_test.go"})
	same(t, foundIn(t, got, "print_steps_hook.go", "type PrintStepsHook struct"), true)
}

func TestAPipeline(t *testing.T) {
	got := add(t, "pipeline", "Pricing")
	same(t, got.Exit, 0)
	same(t, got.Written, []string{"pricing_pipeline.go", "pricing_pipeline_test.go"})
	same(t, foundIn(t, got, "pricing_pipeline.go", "type PricingPipeline struct{}"), true)
}

func TestTheComponentGoesInTheDir(t *testing.T) {
	got := add(t, "filter", "Discount", "src/pricing")
	same(t, got.Exit, 0)
	same(t, got.Written, []string{"src/pricing/discount_filter.go", "src/pricing/discount_filter_test.go"})
	same(t, foundIn(t, got, "src/pricing/discount_filter.go", "type DiscountFilter struct{}"), true)
}

func TestTheDescriptionGoesInTheHeader(t *testing.T) {
	got := add(t, "filter", "Discount", "--description", "Takes a rate off the price.")
	same(t, got.Exit, 0)
	same(t, foundIn(t, got, "discount_filter.go", "Takes a rate off the price."), true)
}

func TestWithNoDescriptionTheHeaderSaysTodo(t *testing.T) {
	got := add(t, "tap", "Audit")
	same(t, got.Exit, 0)
	same(t, foundIn(t, got, "audit_tap.go", "TODO: say what AuditTap does."), true)
}

func TestAnExistingComponentFileIsNotOverwritten(t *testing.T) {
	got := project(t, map[string]string{"discount_filter.go": "existing\n"}, "filter", "Discount")
	same(t, got.Exit, 1)
	same(t, len(got.Written), 0)
	same(t, stringsIn(got.Stderr, "exists"), true)
	same(t, got.text(t, "discount_filter.go"), "existing\n")
	same(t, exists(got, "discount_filter_test.go"), false)
}

func TestAnExistingTestFileStopsBothFiles(t *testing.T) {
	got := project(t, map[string]string{"discount_filter_test.go": "existing\n"}, "filter", "Discount")
	same(t, got.Exit, 1)
	same(t, len(got.Written), 0)
	same(t, stringsIn(got.Stderr, "exists"), true)
	same(t, exists(got, "discount_filter.go"), false)
}

func TestAValveIsNotAType(t *testing.T) {
	got := add(t, "valve", "AtLeast")
	same(t, got.Exit, 2)
	same(t, stringsIn(got.Stderr, "add_valve(predicate, filter)"), true)
}

func TestAPayloadIsNotMadeByAUser(t *testing.T) {
	got := add(t, "payload", "Order")
	same(t, got.Exit, 2)
	same(t, stringsIn(got.Stderr, "runtime"), true)
}

func TestAnUnknownKindIsRefused(t *testing.T) {
	got := add(t, "widget", "Thing")
	same(t, got.Exit, 2)
	same(t, stringsIn(got.Stderr, "filter, predicate, tap, hook"), true)
}

func TestANameThatCannotBeUsedIsRefused(t *testing.T) {
	for _, name := range []string{"2Fast", "Take Rate", ""} {
		got := add(t, "filter", name)
		same(t, got.Exit, 2)
		same(t, stringsIn(got.Stderr, name), true)
	}
}

func TestAMissingNameIsRefused(t *testing.T) {
	got := add(t, "filter")
	same(t, got.Exit, 2)
	same(t, stringsIn(got.Stderr, "name"), true)
}
