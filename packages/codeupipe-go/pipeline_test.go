package codeupipe_test

import (
	"context"
	"errors"
	"sync"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

func run(t *testing.T, pipeline *codeupipe.Pipeline, data map[string]any) *codeupipe.Payload {
	t.Helper()
	out, err := pipeline.Run(context.Background(), codeupipe.NewPayload(data))
	if err != nil {
		t.Fatalf("the run failed: %v", err)
	}
	return out
}

func TestAnEmptyPipelineReturnsTheDataItWasGiven(t *testing.T) {
	out := run(t, codeupipe.NewPipeline(), map[string]any{"a": 1.0})
	same(t, out.ToDict(), map[string]any{"a": 1.0})
}

func TestStepsRunInOrderAndStateRecordsThem(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddFilter(AddFilter{})
	out := run(t, pipeline, nil)
	same(t, out.Get("n"), 2.0)
	same(t, pipeline.State().Executed(), []string{"AddFilter", "AddFilter#2"})
	same(t, pipeline.State().Skipped(), []string{})
	same(t, pipeline.State().Errors(), []codeupipe.StepFailure{})
}

func TestRunWorksOnACopyTheCallersPayloadIsNotChanged(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	given := codeupipe.NewPayload(map[string]any{"n": 1.0})
	out, err := pipeline.Run(context.Background(), given)
	same(t, err, nil)
	same(t, given.Get("n"), 1.0)
	same(t, out.Get("n"), 2.0)
}

func TestAValveRunsItsFilterWhenThePredicateIsTrue(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddValve(IsOnPredicate{}, AddFilter{})
	out := run(t, pipeline, map[string]any{"on": true})
	same(t, out.Get("n"), 1.0)
	same(t, pipeline.State().Executed(), []string{"AddFilter"})
	same(t, pipeline.State().Skipped(), []string{})
}

func TestAValveSkipsItsFilterWhenThePredicateIsFalse(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddValve(IsOnPredicate{}, AddFilter{})
	out := run(t, pipeline, map[string]any{"on": false})
	same(t, out.Has("n"), false)
	same(t, pipeline.State().Executed(), []string{})
	same(t, pipeline.State().Skipped(), []string{"AddFilter"})
}

func TestAFilterFailureStopsTheRunAndStateKeepsTheStepsBeforeIt(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddFilter(FailFilter{})
	pipeline.AddFilter(AddFilter{})
	out, err := pipeline.Run(context.Background(), codeupipe.NewPayload(nil))
	same(t, out, (*codeupipe.Payload)(nil))
	same(t, err, errBoom) // the error itself, so errors.Is works
	same(t, pipeline.State().Executed(), []string{"AddFilter"})
}

func TestATapReadsThePayloadAndCountsAsExecuted(t *testing.T) {
	tap := &SeeTap{}
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddTap(tap)
	run(t, pipeline, nil)
	same(t, tap.seen, []any{1.0})
	same(t, pipeline.State().Executed(), []string{"AddFilter", "SeeTap"})
}

func TestATapFailureIsRecordedAndDoesNotStopTheRun(t *testing.T) {
	hook := &RecordHook{}
	pipeline := codeupipe.NewPipeline()
	pipeline.AddTap(FailTap{})
	pipeline.AddTap(FailTap{})
	pipeline.AddFilter(AddFilter{})
	pipeline.UseHook(hook)
	out := run(t, pipeline, nil)
	same(t, out.Get("n"), 1.0)
	state := pipeline.State()
	same(t, state.Executed(), []string{"FailTap", "FailTap#2", "AddFilter"})
	same(t, len(state.Errors()), 2)
	same(t, state.Errors()[0].Label, "FailTap")
	same(t, state.Errors()[1].Label, "FailTap#2")
	same(t, state.Errors()[0].Err.Error(), "sink is down")
	same(t, hook.events, []string{"before:", "before:AddFilter", "after:AddFilter", "after:"})
}

func TestANestedPipelineIsOneStep(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddPipeline(codeupipe.NewNamedPipeline(InnerPipeline{}))
	pipeline.AddFilter(AddFilter{})
	out := run(t, pipeline, nil)
	same(t, out.Get("n"), 3.0)
	same(t, pipeline.State().Executed(), []string{"InnerPipeline", "AddFilter"})
}

func TestHooksSeeThePipelineAndEachFilterOrValveInOrder(t *testing.T) {
	hook := &RecordHook{}
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddValve(IsOnPredicate{}, FailFilter{})
	pipeline.AddTap(&SeeTap{})
	pipeline.UseHook(hook)
	run(t, pipeline, nil)
	same(t, hook.events, []string{
		"before:", "before:AddFilter", "after:AddFilter",
		"before:FailFilter", "after:FailFilter", "after:",
	})
}

func TestOnAFilterFailureAHookGetsTheStepThenThePipelineAndNoAfter(t *testing.T) {
	hook := &RecordHook{}
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddFilter(FailFilter{})
	pipeline.UseHook(hook)
	_, err := pipeline.Run(context.Background(), codeupipe.NewPayload(nil))
	same(t, err, errBoom)
	same(t, hook.events, []string{
		"before:", "before:AddFilter", "after:AddFilter",
		"before:FailFilter", "error:FailFilter", "error:",
	})
}

// KeepErrorHook keeps each error, and the Payload that OnError sees.
type KeepErrorHook struct {
	codeupipe.HookBase
	errors   []error
	payloads []map[string]any
}

func (h *KeepErrorHook) OnError(_ context.Context, _ string, err error, payload *codeupipe.Payload) {
	h.errors = append(h.errors, err)
	h.payloads = append(h.payloads, payload.ToDict())
}

// WriteThenFailFilter writes, then fails.
type WriteThenFailFilter struct{}

func (WriteThenFailFilter) Call(_ context.Context, payload *codeupipe.Payload) error {
	payload.Insert("written", true)
	return errBoom
}

func TestAHookGetsTheErrorItselfAndThePayloadAsTheFailingStepLeftIt(t *testing.T) {
	hook := &KeepErrorHook{}
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(WriteThenFailFilter{})
	pipeline.UseHook(hook)
	_, err := pipeline.Run(context.Background(), codeupipe.NewPayload(nil))
	same(t, errors.Is(err, errBoom), true)
	same(t, hook.errors, []error{errBoom, errBoom})
	same(t, hook.payloads, []map[string]any{{"written": true}, {"written": true}})
}

func TestAFailureInANestedPipelineLeavesThePayloadOfTheOuterOneAsItWas(t *testing.T) {
	inner := codeupipe.NewPipeline()
	inner.AddFilter(WriteThenFailFilter{})
	hook := &KeepErrorHook{}
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddPipeline(inner)
	pipeline.UseHook(hook)
	_, err := pipeline.Run(context.Background(), codeupipe.NewPayload(nil))
	same(t, err, errBoom)
	same(t, hook.payloads, []map[string]any{{"n": 1.0}, {"n": 1.0}})
	same(t, pipeline.State().Executed(), []string{"AddFilter"})
}

func TestTimingAndLineageAreOffByDefault(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	out := run(t, pipeline, nil)
	same(t, len(pipeline.State().Timings()), 0)
	same(t, out.Lineage(), []string{})
}

func TestObserveTurnsOnTimingAndLineage(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddTap(&SeeTap{})
	pipeline.AddValve(IsOnPredicate{}, FailFilter{})
	pipeline.Observe(true, true)
	out := run(t, pipeline, nil)
	timings := pipeline.State().Timings()
	same(t, len(timings), 2) // a Tap is not timed
	same(t, timings["AddFilter"] >= 0, true)
	same(t, timings["FailFilter"] >= 0, true)
	same(t, out.Lineage(), []string{"AddFilter", "FailFilter"})
}

func TestEachRunStartsWithANewState(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddValve(IsOnPredicate{}, AddFilter{})
	run(t, pipeline, map[string]any{"on": false})
	run(t, pipeline, map[string]any{"on": true})
	same(t, pipeline.State().Executed(), []string{"AddFilter"})
	same(t, pipeline.State().Skipped(), []string{})
}

func TestBeforeAnyRunTheStateIsEmpty(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	same(t, pipeline.State().Executed(), []string{})
}

// -- context ----------------------------------------------------------------

type requestKey struct{}

// SeeRequestFilter, SeeRequestPredicate, SeeRequestTap and SeeRequestHook
// each keep the request of the context that they get.
type SeeRequestFilter struct{ seen *[]any }

func (f SeeRequestFilter) Call(ctx context.Context, _ *codeupipe.Payload) error {
	*f.seen = append(*f.seen, ctx.Value(requestKey{}))
	return nil
}

type SeeRequestPredicate struct{ seen *[]any }

func (q SeeRequestPredicate) Test(ctx context.Context, _ *codeupipe.Payload) bool {
	*q.seen = append(*q.seen, ctx.Value(requestKey{}))
	return true
}

type SeeRequestTap struct{ seen *[]any }

func (t SeeRequestTap) Observe(ctx context.Context, _ *codeupipe.Payload) error {
	*t.seen = append(*t.seen, ctx.Value(requestKey{}))
	return nil
}

type SeeRequestHook struct {
	codeupipe.HookBase
	seen *[]any
}

func (h SeeRequestHook) Before(ctx context.Context, _ string, _ *codeupipe.Payload) {
	*h.seen = append(*h.seen, ctx.Value(requestKey{}))
}

func TestThePipelineGivesTheContextToEachStep(t *testing.T) {
	var seen []any
	inner := codeupipe.NewPipeline()
	inner.AddFilter(SeeRequestFilter{&seen})
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(SeeRequestFilter{&seen})
	pipeline.AddValve(SeeRequestPredicate{&seen}, SeeRequestFilter{&seen})
	pipeline.AddTap(SeeRequestTap{&seen})
	pipeline.AddPipeline(inner)
	pipeline.UseHook(SeeRequestHook{seen: &seen})
	ctx := context.WithValue(context.Background(), requestKey{}, "r-7")
	_, err := pipeline.Run(ctx, codeupipe.NewPayload(nil))
	same(t, err, nil)
	// The Hook before the pipeline and before each of its 3 gated steps, the
	// 2 Filters, the Predicate, the Tap and the Filter of the nested pipeline.
	same(t, len(seen), 9)
	for _, request := range seen {
		same(t, request, "r-7")
	}
}

func TestACancelledContextDoesNotStopTheRun(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddFilter(AddFilter{})
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	out, err := pipeline.Run(ctx, codeupipe.NewPayload(nil))
	same(t, err, nil)
	same(t, out.Get("n"), 2.0)
}

// -- a State belongs to one run ---------------------------------------------

func TestRunsInManyGoroutinesDoNotWriteIntoTheSameState(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddFilter(AddFilter{})
	pipeline.AddTap(FailTap{})
	var wait sync.WaitGroup
	outs := make([]any, 50)
	for i := range outs {
		wait.Add(1)
		go func() {
			defer wait.Done()
			out, err := pipeline.Run(context.Background(), codeupipe.NewPayload(nil))
			if err == nil {
				outs[i] = out.Get("n")
			}
		}()
	}
	wait.Wait()
	for _, n := range outs {
		same(t, n, 2.0)
	}
	state := pipeline.State()
	same(t, state.Executed(), []string{"AddFilter", "AddFilter#2", "FailTap"})
	same(t, len(state.Errors()), 1)
}

// WaitFilter keeps the run of "A" waiting until the test lets it go on.
type WaitFilter struct {
	started chan struct{}
	release chan struct{}
}

func (f WaitFilter) Call(_ context.Context, payload *codeupipe.Payload) error {
	if payload.Get("name") == "A" {
		close(f.started)
		<-f.release
	}
	return nil
}

// FailForBFilter fails for "B".
type FailForBFilter struct{}

func (FailForBFilter) Call(_ context.Context, payload *codeupipe.Payload) error {
	if payload.Get("name") == "B" {
		return errors.New("B fails")
	}
	return nil
}

func TestEachOfTwoRunsAtTheSameTimeWritesIntoTheStateThatItsCallerGave(t *testing.T) {
	wait := WaitFilter{started: make(chan struct{}), release: make(chan struct{})}
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(wait)
	pipeline.AddFilter(FailForBFilter{})
	a, b := codeupipe.NewState(), codeupipe.NewState()
	// A starts first and ends last. B starts second, fails, and ends first.
	done := make(chan error)
	go func() {
		_, err := pipeline.RunWithState(context.Background(), codeupipe.NewPayload(map[string]any{"name": "A"}), a)
		done <- err
	}()
	<-wait.started
	_, err := pipeline.RunWithState(context.Background(), codeupipe.NewPayload(map[string]any{"name": "B"}), b)
	same(t, err.Error(), "B fails")
	close(wait.release)
	same(t, <-done, nil)
	same(t, a.Executed(), []string{"WaitFilter", "FailForBFilter"})
	same(t, b.Executed(), []string{"WaitFilter"})
	same(t, pipeline.State() == b, true) // the State of the run that started last
}

func TestWithNoStateFromTheCallerARunMakesANewOne(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(FailForBFilter{})
	given := codeupipe.NewState()
	_, err := pipeline.RunWithState(context.Background(), codeupipe.NewPayload(map[string]any{"name": "A"}), given)
	same(t, err, nil)
	same(t, pipeline.State() == given, true)
	run(t, pipeline, map[string]any{"name": "A"})
	same(t, pipeline.State() == given, false)
	same(t, given.Executed(), []string{"FailForBFilter"})
	same(t, pipeline.State().Executed(), []string{"FailForBFilter"})
}

func TestRunWithStateNeedsAState(t *testing.T) {
	defer func() {
		same(t, recover(), "codeupipe: RunWithState needs a State. NewState makes one")
	}()
	_, _ = codeupipe.NewPipeline().RunWithState(context.Background(), codeupipe.NewPayload(nil), nil)
}
