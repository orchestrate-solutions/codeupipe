package main

import (
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// parsed gives the four keys that ParseArgumentsFilter makes from arguments,
// or the exit code and the message of a refusal.
func parsed(t *testing.T, args ...string) (kind, name, dir, description string, code int, stderr string) {
	t.Helper()
	out, refusal := runStep(ParseArgumentsFilter{}, codeupipe.NewPayload(map[string]any{"args": args}))
	if refusal != nil {
		return "", "", "", "", refusal.ExitCode, refusal.Message
	}
	return text(out, "kind"), text(out, "name"), text(out, "directory"), text(out, "description"), 0, ""
}

func TestItReadsKindNameDirAndDescription(t *testing.T) {
	kind, name, dir, description, code, _ := parsed(t, "filter", "Discount", "src/pricing",
		"--description", "Takes a rate off the price.")
	same(t, code, 0)
	same(t, []string{kind, name, dir, description},
		[]string{"filter", "Discount", "src/pricing", "Takes a rate off the price."})
}

func TestTheDefaultDirIsTheRootAndTheDescriptionIsEmpty(t *testing.T) {
	kind, name, dir, description, code, _ := parsed(t, "tap", "Audit")
	same(t, code, 0)
	same(t, []string{kind, name, dir, description}, []string{"tap", "Audit", ".", ""})
}

func TestDescriptionBeforeTheNamesIsReadToo(t *testing.T) {
	kind, name, dir, description, code, _ := parsed(t, "--description", "Reads the log.", "tap", "Audit")
	same(t, code, 0)
	same(t, []string{kind, name, dir, description}, []string{"tap", "Audit", ".", "Reads the log."})
}

func TestNoArgumentsIsRefused(t *testing.T) {
	_, _, _, _, code, stderr := parsed(t)
	same(t, code, 2)
	same(t, stringsIn(stderr, "kind"), true)
}

func TestStepAMissingNameIsRefused(t *testing.T) {
	_, _, _, _, code, stderr := parsed(t, "filter")
	same(t, code, 2)
	same(t, stringsIn(stderr, "name"), true)
}

func TestATooLongArgumentListIsRefused(t *testing.T) {
	_, _, _, _, code, stderr := parsed(t, "filter", "Discount", "src", "extra")
	same(t, code, 2)
	same(t, stringsIn(stderr, "Too many arguments"), true)
}

func TestTheStepKeepsThePayloadItWasGiven(t *testing.T) {
	in := codeupipe.NewPayload(map[string]any{"args": []string{"tap", "Audit"}})
	out, refusal := runStep(ParseArgumentsFilter{}, in)
	same(t, refusal == nil, true)
	same(t, out == in, true)
	same(t, text(out, "kind"), "tap")
}
