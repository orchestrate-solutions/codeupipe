package codeupipelint

import (
	"strings"
	"testing"
)

// Each method that must only read: Test, Observe, Before, After and OnError.
func TestI004EachMethodThatMustOnlyReadFlagsAWrite(t *testing.T) {
	got := lintIn(t, map[string]string{
		"seen.go": `package demo

type Seen struct{}

func (s Seen) Test(ctx context.Context, payload *codeupipe.Payload) bool {
	payload.Insert("seen", true)
	return true
}

func (s Seen) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert("seen", true)
	return nil
}

func (s Seen) Before(ctx context.Context, step string, payload *codeupipe.Payload) {
	payload.Insert("seen", true)
}

func (s Seen) After(ctx context.Context, step string, payload *codeupipe.Payload) {
	payload.Insert("seen", true)
}

func (s Seen) OnError(ctx context.Context, step string, err error, payload *codeupipe.Payload) {
	payload.Insert("seen", true)
}
`,
	}, LintOptions{})
	sameFound(t, got,
		"seen.go:6 CUP-I004",
		"seen.go:11 CUP-I004",
		"seen.go:16 CUP-I004",
		"seen.go:20 CUP-I004",
		"seen.go:24 CUP-I004",
	)
}

func TestI004AFilterThatWritesGivesNoFinding(t *testing.T) {
	got := lintIn(t, map[string]string{
		"mark.go": `package demo

type Mark struct{}

func (m Mark) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert("seen", true)
	payload.Remove("old")
	return nil
}
`,
	}, LintOptions{})
	sameFound(t, got)
}

func TestI004AWriteToACopyGivesNoFinding(t *testing.T) {
	got := lintIn(t, map[string]string{
		"audit.go": `package demo

type Audit struct{}

func (a Audit) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	copied := payload.Copy()
	copied.Insert("seen", true)
	return nil
}
`,
	}, LintOptions{})
	sameFound(t, got)
}

func TestI004AnUnnamedPayloadParameterGivesNoFinding(t *testing.T) {
	got := lintIn(t, map[string]string{
		"quiet.go": `package demo

type Quiet struct{}

func (q Quiet) Test(ctx context.Context, _ *codeupipe.Payload) bool {
	other := codeupipe.NewPayload(nil)
	other.Insert("seen", true)
	return true
}
`,
		"unnamed.go": `package demo

type Unnamed struct{}

func (u Unnamed) Observe(context.Context, *codeupipe.Payload) error {
	return nil
}
`,
	}, LintOptions{})
	sameFound(t, got)
}

func TestI004AChainGivesOneFindingAtTheFirstCall(t *testing.T) {
	got := lintIn(t, map[string]string{
		"audit.go": `package demo

type Audit struct{}

func (a Audit) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert("a", 1).Insert("b", 2).Remove("c")
	return nil
}
`,
	}, LintOptions{})
	sameFound(t, got, "audit.go:6 CUP-I004")
	if !strings.HasPrefix(got.findings[0].Message, "Tap `Audit` writes to its payload in `Observe`: `payload.Insert(\"a\", 1)`. Only a Filter writes") {
		t.Fatalf("message %q", got.findings[0].Message)
	}
}

// A pipeline of a type of its own, in place of the Payload.
func TestI004AnAssignmentOrIncDecToTheValueFlags(t *testing.T) {
	got := lintIn(t, map[string]string{
		"order_tap.go": `package demo

type Order struct {
	Bulk  bool
	Items []int
	Count int
}

type OrderTap struct{}

func (t OrderTap) Observe(ctx context.Context, order *Order) error {
	order.Bulk = true
	order.Items[0] = 1
	order.Count++
	*order = Order{}
	return nil
}
`,
	}, LintOptions{})
	sameFound(t, got,
		"order_tap.go:12 CUP-I004",
		"order_tap.go:13 CUP-I004",
		"order_tap.go:14 CUP-I004",
		"order_tap.go:15 CUP-I004",
	)
	if !strings.HasPrefix(got.findings[0].Message, "Tap `OrderTap` writes to its payload in `Observe`: `order.Bulk = true`. ") {
		t.Fatalf("message %q", got.findings[0].Message)
	}
}

// A function literal with a parameter of the same name is another value.
func TestI004AFunctionLiteralParameterShadowsThePayload(t *testing.T) {
	got := lintIn(t, map[string]string{
		"audit.go": `package demo

type Audit struct{}

func (a Audit) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	later := func(payload *codeupipe.Payload) {
		payload.Insert("inner", 1)
	}
	later(nil)
	again := func() {
		payload.Insert("outer", 2)
	}
	again()
	return nil
}
`,
	}, LintOptions{})
	sameFound(t, got, "audit.go:11 CUP-I004")
}

func TestI004AMethodThatIsNotAStepGivesNoFinding(t *testing.T) {
	got := lintIn(t, map[string]string{
		"store.go": `package demo

type Store struct{}

func (s Store) Save(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert("saved", true)
	return nil
}
`,
	}, LintOptions{})
	sameFound(t, got)
}

// The comment that allows a CUP-I003 finding allows a CUP-I004 finding too.
func TestI004EachInvariantMarkerAllowsTheWrite(t *testing.T) {
	for _, marker := range []string{"allow-state-read", "allow-shared-file", "allow-name", "allow-plain"} {
		got := lintIn(t, map[string]string{
			"audit.go": `package demo

type Audit struct{}

func (a Audit) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert("seen", true) // cup: ` + marker + ` the audit needs the flag
	return nil
}
`,
		}, LintOptions{})
		sameFound(t, got)
		if got.suppressed != 1 {
			t.Fatalf("%s: suppressed %d, want 1", marker, got.suppressed)
		}
	}
}
