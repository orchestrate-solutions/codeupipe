package codeupipelint

import (
	"strings"
	"testing"
)

// The Rust test i003_a_filter_or_a_predicate_that_reads_state, in Go.
func TestI003AFilterOrAPredicateThatReadsState(t *testing.T) {
	got := lintIn(t, map[string]string{
		"count_filter.go": `package demo

type CountFilter struct {
	pipeline *codeupipe.Pipeline
	seen     *codeupipe.State
	states   []codeupipe.State
}

func (f CountFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert("a", len(f.pipeline.State().Executed()))
	payload.Insert("b", len(f.seen.Skipped()))
	payload.Insert("c", len(f.states))
	payload.Insert("d", payload.Has("state"))
	state := codeupipe.NewState()
	payload.Insert("e", len(state.Executed())+len(f.State()))
	return nil
}
`,
		"ran_predicate.go": `package demo

type RanPredicate struct {
	holder *Holder
}

func (p RanPredicate) Test(ctx context.Context, payload *codeupipe.Payload) bool {
	return len(p.holder.State().Executed()) > 0
}
`,
		"watch_tap.go": `package demo

type WatchTap struct {
	pipeline *codeupipe.Pipeline
}

func (t WatchTap) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	fmt.Println(t.pipeline.State().Executed())
	return nil
}
`,
		"log_hook.go": `package demo

type LogHook struct {
	pipeline *codeupipe.Pipeline
}

func (h LogHook) After(ctx context.Context, step string, payload *codeupipe.Payload) {
	fmt.Println(h.pipeline.State().Executed())
}
`,
	}, otherRulesOff)
	sameFound(t, got,
		"count_filter.go:10 CUP-I003",
		"count_filter.go:11 CUP-I003",
		"count_filter.go:15 CUP-I003",
		"ran_predicate.go:8 CUP-I003",
	)
	if !strings.HasPrefix(got.findings[0].Message, "Filter `CountFilter` reads the State of a pipeline in `Call`: `f.pipeline.State()`. A Filter's result") {
		t.Fatalf("message %q", got.findings[0].Message)
	}
	if !strings.HasPrefix(got.findings[1].Message, "Filter `CountFilter` reads the State of a pipeline in `Call`: `f.seen`. ") {
		t.Fatalf("message %q", got.findings[1].Message)
	}
	if !strings.HasPrefix(got.findings[3].Message, "Predicate `RanPredicate` reads the State of a pipeline in `Test`: `p.holder.State()`. ") {
		t.Fatalf("message %q", got.findings[3].Message)
	}
}

func TestI003AFieldThatHoldsAStateIsRead(t *testing.T) {
	got := lintIn(t, map[string]string{
		"fields.go": `package demo

type Fields struct {
	a *codeupipe.State
	b codeupipe.State
	c State
	d *State
	e []codeupipe.State
	f *codeupipe.Pipeline
}

func (x Fields) Call(ctx context.Context, payload *codeupipe.Payload) error {
	use(x.a)
	use(x.b)
	use(x.c)
	use(x.d)
	use(x.e)
	use(x.f)
	return nil
}
`,
	}, otherRulesOff)
	sameFound(t, got,
		"fields.go:13 CUP-I003",
		"fields.go:14 CUP-I003",
		"fields.go:15 CUP-I003",
		"fields.go:16 CUP-I003",
	)
}

func TestI003AStructInAnotherFileGivesNoFieldFinding(t *testing.T) {
	got := lintIn(t, map[string]string{
		"fields.go": `package demo

type Remote struct {
	seen *codeupipe.State
}
`,
		"remote_filter.go": `package demo

func (r Remote) Call(ctx context.Context, payload *codeupipe.Payload) error {
	use(r.seen)
	return nil
}
`,
	}, otherRulesOff)
	sameFound(t, got)
}

func TestI003AFunctionThatIsNotAStepGivesNoFinding(t *testing.T) {
	got := lintIn(t, map[string]string{
		"plain.go": `package demo

type Holder struct {
	pipeline *codeupipe.Pipeline
}

func run(h Holder) {
	h.pipeline.State()
}
`,
	}, otherRulesOff)
	sameFound(t, got)
}

func TestI003AllowedByAStateReadMarker(t *testing.T) {
	got := lintIn(t, map[string]string{
		"allowed.go": `package demo

type Count struct {
	pipeline *codeupipe.Pipeline
}

func (c Count) Call(ctx context.Context, payload *codeupipe.Payload) error {
	// cup: allow-state-read the count is the pipeline's own
	payload.Insert("n", len(c.pipeline.State().Executed()))
	return nil
}
`,
	}, otherRulesOff)
	sameFound(t, got)
	if got.suppressed != 1 {
		t.Fatalf("suppressed %d, want 1", got.suppressed)
	}
}

// otherRulesOff switches off the file and name rules, so that the example
// files of these tests can be short.
var otherRulesOff = disable(OnePrimitivePerFile, PrimitiveFileName, PrimitiveRoleSuffix, LogicOutsidePrimitive)
