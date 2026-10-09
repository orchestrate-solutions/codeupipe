package codeupipe

import (
	"errors"
	"reflect"
	"testing"
)

// -----------------------------------------------------------------------
// Test helpers — mock filter, tap, hook
// -----------------------------------------------------------------------

// addFilter is a simple test filter that adds a key-value pair.
type addFilter struct {
	key   string
	value any
}

func (f *addFilter) Call(p Payload) (Payload, error) {
	return p.Insert(f.key, f.value), nil
}
func (f *addFilter) Name() string { return "AddFilter(" + f.key + ")" }

// errorFilter always returns an error.
type errorFilter struct{ msg string }

func (f *errorFilter) Call(_ Payload) (Payload, error) {
	return Payload{}, errors.New(f.msg)
}
func (f *errorFilter) Name() string { return "ErrorFilter" }

// doubleFilter is a stream filter that yields 2 copies.
type doubleFilter struct{}

func (f *doubleFilter) Stream(chunk Payload) ([]Payload, error) {
	return []Payload{chunk, chunk}, nil
}

// dropFilter is a stream filter that drops everything.
type dropFilter struct{}

func (f *dropFilter) Stream(_ Payload) ([]Payload, error) {
	return nil, nil
}

// recordingTap records all payloads it observes.
type recordingTap struct {
	observed []Payload
}

func (t *recordingTap) Observe(p Payload) {
	t.observed = append(t.observed, p)
}

// recordingHook records lifecycle calls.
type recordingHook struct {
	DefaultHook
	calls []string
}

func (h *recordingHook) Before(filterName string, _ Payload) {
	h.calls = append(h.calls, "before:"+filterName)
}
func (h *recordingHook) After(filterName string, _ Payload) {
	h.calls = append(h.calls, "after:"+filterName)
}
func (h *recordingHook) OnError(filterName string, _ error, _ Payload) {
	h.calls = append(h.calls, "error:"+filterName)
}

// -----------------------------------------------------------------------
// Valve tests
// -----------------------------------------------------------------------

// Valve predicates are objects: named types with Test (conformance/API.md).
type goIsTrue struct{}

func (goIsTrue) Test(p Payload) bool { return p.Get("go") == true }

type isOpen struct{}

func (isOpen) Test(p Payload) bool { return p.Get("open") == true }

type always struct{}

func (always) Test(Payload) bool { return true }

// subPipeline is a named pipeline type, so it can be nested.
type subPipeline struct{ *Pipeline }

func TestValvePredicateTrue(t *testing.T) {
	inner := &addFilter{key: "result", value: "done"}
	v := NewValve(inner, goIsTrue{})

	p := NewPayload(map[string]any{"go": true})
	result, err := v.Call(p)
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("result") != "done" {
		t.Fatal("inner filter should have run")
	}
	if v.LastSkipped {
		t.Fatal("should not be skipped")
	}
}

func TestValvePredicateFalse(t *testing.T) {
	inner := &addFilter{key: "result", value: "done"}
	v := NewValve(inner, goIsTrue{})

	p := NewPayload(map[string]any{"go": false})
	result, err := v.Call(p)
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("result") != nil {
		t.Fatal("inner filter should NOT have run")
	}
	if !v.LastSkipped {
		t.Fatal("should be skipped")
	}
}

func TestValveString(t *testing.T) {
	v := NewValve(&addFilter{}, always{})
	s := v.String()
	if s != "Valve("+here+"addFilter, "+here+"always)" {
		t.Fatalf("unexpected string: %s", s)
	}
}

// -----------------------------------------------------------------------
// Pipeline batch tests
// -----------------------------------------------------------------------

func TestPipelineEmpty(t *testing.T) {
	p := NewPipeline()
	result, err := p.Run(NewPayload(map[string]any{"x": 1}))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("x") != 1 {
		t.Fatal("payload should pass through empty pipeline")
	}
}

func TestPipelineSingleFilter(t *testing.T) {
	p := NewPipeline().AddFilter(&addFilter{key: "added", value: "yes"})
	result, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("added") != "yes" {
		t.Fatal("filter didn't run")
	}
	if len(p.State().Executed) != 1 {
		t.Fatal("expected 1 executed")
	}
}

func TestPipelineMultipleFilters(t *testing.T) {
	p := NewPipeline().AddFilter(
		&addFilter{key: "a", value: 1}).AddFilter(

		&addFilter{key: "b", value: 2})

	result, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("a") != 1 || result.Get("b") != 2 {
		t.Fatal("both filters should have run")
	}
	if len(p.State().Executed) != 2 {
		t.Fatalf("expected 2 executed, got %d", len(p.State().Executed))
	}
}

func TestPipelineTap(t *testing.T) {
	tap := &recordingTap{}
	p := NewPipeline().AddFilter(
		&addFilter{key: "x", value: 1}).AddTap(

		tap)

	_, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if len(tap.observed) != 1 {
		t.Fatal("tap should have been called once")
	}
	if tap.observed[0].Get("x") != 1 {
		t.Fatal("tap saw wrong payload")
	}
}

func TestPipelineDisabledTap(t *testing.T) {
	tap := &recordingTap{}
	p := NewPipeline().AddTap(
		tap).
		DisableTaps(here + "recordingTap")

	_, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if len(tap.observed) != 0 {
		t.Fatal("disabled tap should not have been called")
	}
	if len(p.State().Skipped) != 1 || p.State().Skipped[0] != here+"recordingTap" {
		t.Fatal("disabled tap should be in skipped")
	}
}

func TestPipelineEnableTap(t *testing.T) {
	tap := &recordingTap{}
	p := NewPipeline().AddTap(
		tap).
		DisableTaps(here + "recordingTap").
		EnableTaps(here + "recordingTap")

	_, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if len(tap.observed) != 1 {
		t.Fatal("re-enabled tap should have been called")
	}
}

func TestPipelineValveExecution(t *testing.T) {
	inner := &addFilter{key: "gated", value: "yes"}
	v := NewValve(inner, isOpen{})

	p := NewPipeline().AddFilter(v)
	result, err := p.Run(NewPayload(map[string]any{"open": true}))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("gated") != "yes" {
		t.Fatal("valve should have executed")
	}
	if len(p.State().Executed) != 1 {
		t.Fatal("valve should be in executed")
	}
}

func TestPipelineValveSkip(t *testing.T) {
	inner := &addFilter{key: "gated", value: "yes"}
	v := NewValve(inner, isOpen{})

	p := NewPipeline().AddFilter(v)
	result, err := p.Run(NewPayload(map[string]any{"open": false}))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("gated") != nil {
		t.Fatal("valve should have skipped")
	}
	if len(p.State().Skipped) != 1 || p.State().Skipped[0] != here+"addFilter" {
		t.Fatal("valve should be in skipped")
	}
}

func TestPipelineHooksOrder(t *testing.T) {
	hook := &recordingHook{}
	p := NewPipeline().AddFilter(
		&addFilter{key: "x", value: 1}).
		UseHook(hook)

	_, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}

	expected := []string{
		"before:",                      // pipeline start
		"before:" + here + "addFilter", // filter start: hooks receive the identity
		"after:" + here + "addFilter",  // filter end
		"after:",                       // pipeline end
	}
	if len(hook.calls) != len(expected) {
		t.Fatalf("expected %d calls, got %d: %v", len(expected), len(hook.calls), hook.calls)
	}
	for i, exp := range expected {
		if hook.calls[i] != exp {
			t.Fatalf("call %d: expected %q, got %q", i, exp, hook.calls[i])
		}
	}
}

func TestPipelineHooksOnError(t *testing.T) {
	hook := &recordingHook{}
	p := NewPipeline().AddFilter(
		&errorFilter{msg: "kaboom"}).
		UseHook(hook)

	_, err := p.Run(NewPayload(nil))
	if err == nil {
		t.Fatal("expected error")
	}

	// Should have: before: (pipeline start), before:BadFilter, error:BadFilter
	found := false
	for _, c := range hook.calls {
		if c == "error:"+here+"errorFilter" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected error hook call, got %v", hook.calls)
	}
}

func TestPipelineParallel(t *testing.T) {
	p := NewPipeline().AddParallel(
		[]Filter{
			&addFilter{key: "a", value: 1},
			&addFilter{key: "b", value: 2},
		})

	result, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("a") != 1 || result.Get("b") != 2 {
		t.Fatal("parallel filters should both have run")
	}
}

func TestPipelineNestedPipeline(t *testing.T) {
	child := subPipeline{NewPipeline().AddFilter(&addFilter{key: "inner", value: "done"})}
	parent := NewPipeline().AddFilter(
		&addFilter{key: "outer", value: "done"}).AddPipeline(

		child)

	result, err := parent.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("outer") != "done" || result.Get("inner") != "done" {
		t.Fatal("nested pipeline should run")
	}
}

func TestPipelineObserveTiming(t *testing.T) {
	p := NewPipeline().
		Observe(true, false).AddFilter(

		&addFilter{key: "x", value: 1})

	_, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := p.State().Timings[here+"addFilter"]; !ok {
		t.Fatal("timing not recorded")
	}
}

func TestPipelineObserveLineage(t *testing.T) {
	p := NewPipeline().
		Observe(false, true).AddFilter(

		&addFilter{key: "x", value: 1}).AddFilter(

		&addFilter{key: "y", value: 2})

	result, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	lin := result.Lineage()
	if len(lin) != 2 || lin[0] != here+"addFilter" || lin[1] != here+"addFilter#2" {
		t.Fatalf("expected [addFilter, addFilter#2], got %v", lin)
	}
}

func TestPipelineStreamFilterRejectedInBatch(t *testing.T) {
	p := NewPipeline().AddStreamFilter(&doubleFilter{})
	_, err := p.Run(NewPayload(nil))
	if err == nil {
		t.Fatal("expected error for StreamFilter in batch mode")
	}
}

func TestPipelineErrorPropagation(t *testing.T) {
	p := NewPipeline().AddFilter(
		&addFilter{key: "a", value: 1}).AddFilter(

		&errorFilter{msg: "fail"})

	_, err := p.Run(NewPayload(nil))
	if err == nil || err.Error() != "fail" {
		t.Fatalf("expected 'fail' error, got %v", err)
	}
}

func TestPipelineStateReset(t *testing.T) {
	p := NewPipeline().AddFilter(&addFilter{key: "x", value: 1})

	p.Run(NewPayload(nil))
	if len(p.State().Executed) != 1 {
		t.Fatal("first run should have 1 executed")
	}

	p.Run(NewPayload(nil))
	if len(p.State().Executed) != 1 {
		t.Fatal("state should reset between runs")
	}
}

func TestPipelineDescribe(t *testing.T) {
	child := subPipeline{NewPipeline().AddFilter(&addFilter{key: "x", value: 1})}
	p := NewPipeline().AddFilter(
		&addFilter{key: "a", value: 1}).AddTap(

		&recordingTap{}).AddParallel(

		[]Filter{&addFilter{key: "b", value: 2}}).
		AddPipeline(

			child)

	desc := p.Describe()
	if desc.StepCount != 4 {
		t.Fatalf("expected 4 steps, got %d", desc.StepCount)
	}
	if desc.Steps[0].Type != "filter" {
		t.Fatal("first step should be filter")
	}
	if desc.Steps[1].Type != "tap" {
		t.Fatal("second step should be tap")
	}
	if desc.Steps[2].Type != "parallel" {
		t.Fatal("third step should be parallel")
	}
	if desc.Steps[3].Type != "pipeline" {
		t.Fatal("fourth step should be pipeline")
	}
}

func TestPipelineFluentBuilder(t *testing.T) {
	tap := &recordingTap{}
	hook := &recordingHook{}

	p := NewPipeline().AddFilter(
		&addFilter{key: "a", value: 1}).AddTap(

		tap).
		UseHook(hook).
		Observe(true, true)

	result, err := p.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("a") != 1 {
		t.Fatal("fluent builder pipeline failed")
	}
}

// -----------------------------------------------------------------------
// Streaming tests
// -----------------------------------------------------------------------

func TestPipelineStreamRegular(t *testing.T) {
	p := NewPipeline().AddFilter(&addFilter{key: "processed", value: true})

	source := make(chan Payload, 3)
	source <- NewPayload(map[string]any{"id": 1})
	source <- NewPayload(map[string]any{"id": 2})
	source <- NewPayload(map[string]any{"id": 3})
	close(source)

	out, errCh := p.Stream(source)

	var results []Payload
	for r := range out {
		results = append(results, r)
	}

	select {
	case err := <-errCh:
		if err != nil {
			t.Fatal(err)
		}
	default:
	}

	if len(results) != 3 {
		t.Fatalf("expected 3 results, got %d", len(results))
	}
	for _, r := range results {
		if r.Get("processed") != true {
			t.Fatal("filter didn't process")
		}
	}
}

func TestPipelineStreamFanOut(t *testing.T) {
	p := NewPipeline().AddStreamFilter(&doubleFilter{})

	source := make(chan Payload, 2)
	source <- NewPayload(map[string]any{"x": 1})
	source <- NewPayload(map[string]any{"x": 2})
	close(source)

	out, _ := p.Stream(source)
	var results []Payload
	for r := range out {
		results = append(results, r)
	}

	if len(results) != 4 {
		t.Fatalf("expected 4 (2 doubled), got %d", len(results))
	}
}

func TestPipelineStreamDrop(t *testing.T) {
	p := NewPipeline().AddStreamFilter(&dropFilter{})

	source := make(chan Payload, 2)
	source <- NewPayload(map[string]any{"x": 1})
	source <- NewPayload(map[string]any{"x": 2})
	close(source)

	out, _ := p.Stream(source)
	var results []Payload
	for r := range out {
		results = append(results, r)
	}

	if len(results) != 0 {
		t.Fatalf("expected 0 (all dropped), got %d", len(results))
	}
}

func TestPipelineStreamTap(t *testing.T) {
	tap := &recordingTap{}
	p := NewPipeline().AddTap(tap)

	source := make(chan Payload, 2)
	source <- NewPayload(map[string]any{"x": 1})
	source <- NewPayload(map[string]any{"x": 2})
	close(source)

	out, _ := p.Stream(source)
	for range out {
	}

	if len(tap.observed) != 2 {
		t.Fatalf("expected 2 observations, got %d", len(tap.observed))
	}
}

func TestPipelineStreamDisabledTap(t *testing.T) {
	tap := &recordingTap{}
	p := NewPipeline().AddTap(
		tap).
		DisableTaps(here + "recordingTap")

	source := make(chan Payload, 1)
	source <- NewPayload(nil)
	close(source)

	out, _ := p.Stream(source)
	for range out {
	}

	if len(tap.observed) != 0 {
		t.Fatal("disabled tap should not observe")
	}
}

func TestPipelineStreamHooksCalledOnce(t *testing.T) {
	hook := &recordingHook{}
	p := NewPipeline().AddFilter(
		&addFilter{key: "x", value: 1}).
		UseHook(hook)

	source := make(chan Payload, 1)
	source <- NewPayload(nil)
	close(source)

	out, _ := p.Stream(source)
	for range out {
	}

	// Pipeline-level hooks: before:"" and after:""
	var beforePipe, afterPipe int
	for _, c := range hook.calls {
		if c == "before:" {
			beforePipe++
		}
		if c == "after:" {
			afterPipe++
		}
	}
	if beforePipe != 1 || afterPipe != 1 {
		t.Fatalf("expected 1 pipeline before + 1 after, got %d + %d, calls=%v",
			beforePipe, afterPipe, hook.calls)
	}
}

func TestPipelineStreamParallel(t *testing.T) {
	p := NewPipeline().AddParallel(
		[]Filter{
			&addFilter{key: "a", value: 1},
			&addFilter{key: "b", value: 2},
		})

	source := make(chan Payload, 1)
	source <- NewPayload(nil)
	close(source)

	out, _ := p.Stream(source)
	var results []Payload
	for r := range out {
		results = append(results, r)
	}

	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].Get("a") != 1 || results[0].Get("b") != 2 {
		t.Fatal("parallel should merge both")
	}
}

func TestPipelineStreamNested(t *testing.T) {
	child := subPipeline{NewPipeline().AddFilter(&addFilter{key: "inner", value: true})}
	p := NewPipeline().AddPipeline(child)

	source := make(chan Payload, 1)
	source <- NewPayload(nil)
	close(source)

	out, _ := p.Stream(source)
	var results []Payload
	for r := range out {
		results = append(results, r)
	}

	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].Get("inner") != true {
		t.Fatal("nested pipeline should run")
	}
}

// -----------------------------------------------------------------------
// Call (nesting alias)
// -----------------------------------------------------------------------

func TestPipelineCallIsAlias(t *testing.T) {
	p := NewPipeline().AddFilter(&addFilter{key: "via", value: "call"})
	result, err := p.Call(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if result.Get("via") != "call" {
		t.Fatal("Call should work like Run")
	}
}

// -----------------------------------------------------------------------
// Plane B — a Tap failure never halts the pipeline
// -----------------------------------------------------------------------

// panickingTap fails the way a Go Tap fails: Observe has no error return.
type panickingTap struct{ message string }

func (t *panickingTap) Observe(_ Payload) { panic(t.message) }

// A Tap that panics is recorded in State.Errors under its name, still counts
// as executed, and the run continues — the same contract as Python
// codeupipe.core. Cross-runtime cases: conformance/cases/tap.json.
func TestPipelineTapPanicIsContained(t *testing.T) {
	p := NewPipeline()
	p.AddFilter(&addFilter{"a", 1.0})
	p.AddTap(&panickingTap{"sink down"})
	p.AddFilter(&addFilter{"b", 2.0})

	out, err := p.Run(NewPayload(nil))

	if err != nil {
		t.Fatalf("a tap failure halted the run: %v", err)
	}
	if out.Get("b") != 2.0 {
		t.Fatalf("steps after the tap did not run: %v", out.ToDict())
	}
	errs := p.State().Errors
	if len(errs) != 1 || errs[0].Name != here+"panickingTap" {
		t.Fatalf("tap failure not recorded as a State error: %+v", errs)
	}
	executed := p.State().Executed
	if len(executed) != 3 || executed[1] != here+"panickingTap" {
		t.Fatalf("tap should count as executed: %v", executed)
	}
}

func TestPipelineStreamTapPanicIsContained(t *testing.T) {
	p := NewPipeline()
	p.AddTap(&panickingTap{"sink down"})

	source := make(chan Payload, 3)
	for i := 0; i < 3; i++ {
		source <- NewPayload(map[string]any{"n": float64(i)})
	}
	close(source)

	out, errCh := p.Stream(source)
	var seen []any
	for chunk := range out {
		seen = append(seen, chunk.Get("n"))
	}
	// Stream only sends on errCh when a step fails and never closes it.
	select {
	case err := <-errCh:
		t.Fatalf("stream failed: %v", err)
	default:
	}
	if len(seen) != 3 {
		t.Fatalf("a tap failure dropped chunks: %v", seen)
	}
	if len(p.State().Errors) != 3 {
		t.Fatalf("each chunk's tap failure should be recorded: %+v", p.State().Errors)
	}
}

// On a failure, OnError fires for the failing step and then for the pipeline
// (filterName ""), mirroring Before/After, which fire at both levels. Same
// contract in every runtime: conformance/cases/hook.json.
func TestPipelineOnErrorFiresForStepThenPipeline(t *testing.T) {
	hook := &recordingHook{}
	p := NewPipeline().AddFilter(
		&addFilter{"a", 1.0}).AddFilter(

		&errorFilter{msg: "kaboom"}).
		UseHook(hook)

	if _, err := p.Run(NewPayload(nil)); err == nil {
		t.Fatal("expected error")
	}

	a, b := here+"addFilter", here+"errorFilter"
	want := []string{"before:", "before:" + a, "after:" + a, "before:" + b, "error:" + b, "error:"}
	if !reflect.DeepEqual(hook.calls, want) {
		t.Fatalf("hook calls\n got %v\nwant %v", hook.calls, want)
	}
}

func TestPipelineOnErrorNamesAFailingNestedPipeline(t *testing.T) {
	hook := &recordingHook{}
	child := subPipeline{NewPipeline().AddFilter(&errorFilter{msg: "inner"})}
	p := NewPipeline().AddPipeline(child).UseHook(hook)

	if _, err := p.Run(NewPayload(nil)); err == nil {
		t.Fatal("expected error")
	}

	sub := here + "subPipeline"
	want := []string{"before:", "before:" + sub, "error:" + sub, "error:"}
	if !reflect.DeepEqual(hook.calls, want) {
		t.Fatalf("hook calls\n got %v\nwant %v", hook.calls, want)
	}
}

// -----------------------------------------------------------------------
// API contract (conformance/API.md): Go spellings
// -----------------------------------------------------------------------

func TestPayloadRemoveHasToDict(t *testing.T) {
	p := NewPayload(map[string]any{"a": nil, "b": 2.0})
	if !p.Has("a") || p.Has("zz") {
		t.Fatalf("Has should see present keys, including nil values")
	}
	without := p.Remove("a")
	if !reflect.DeepEqual(without.ToDict(), map[string]any{"b": 2.0}) {
		t.Fatalf("Remove: got %v", without.ToDict())
	}
	if !p.Has("a") {
		t.Fatalf("Remove must return a new Payload")
	}
}

func TestMutablePayloadRemoveHas(t *testing.T) {
	m := NewPayload(map[string]any{"a": 1.0}).WithMutation()
	m.Set("k", "v")
	m.Remove("a")
	if m.Has("a") || !m.Has("k") {
		t.Fatalf("MutablePayload.Remove/Has")
	}
	if !reflect.DeepEqual(m.ToImmutable().ToDict(), map[string]any{"k": "v"}) {
		t.Fatalf("got %v", m.ToImmutable().ToDict())
	}
}
