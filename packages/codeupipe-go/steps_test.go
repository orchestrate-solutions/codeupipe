package codeupipe_test

import (
	"context"
	"errors"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// The steps that the tests of the Pipeline and of the labels share.

var errBoom = errors.New("boom")

// AddFilter adds 1 to "n".
type AddFilter struct{}

func (AddFilter) Call(_ context.Context, payload *codeupipe.Payload) error {
	n, _ := payload.Get("n").(float64)
	payload.Insert("n", n+1)
	return nil
}

// FailFilter fails with errBoom.
type FailFilter struct{}

func (FailFilter) Call(context.Context, *codeupipe.Payload) error {
	return errBoom
}

// IsOnPredicate is true when "on" is true.
type IsOnPredicate struct{}

func (IsOnPredicate) Test(_ context.Context, payload *codeupipe.Payload) bool {
	return payload.Get("on") == true
}

// SeeTap keeps each value of "n" that it sees.
type SeeTap struct {
	seen []any
}

func (t *SeeTap) Observe(_ context.Context, payload *codeupipe.Payload) error {
	t.seen = append(t.seen, payload.Get("n"))
	return nil
}

// FailTap fails.
type FailTap struct{}

func (FailTap) Observe(context.Context, *codeupipe.Payload) error {
	return errors.New("sink is down")
}

// InnerPipeline adds 1 to "n" two times.
type InnerPipeline struct{}

func (InnerPipeline) AddSteps(pipeline *codeupipe.Pipeline) {
	pipeline.AddFilter(AddFilter{})
	pipeline.AddFilter(AddFilter{})
}

// RecordHook keeps each event as "before:<step>", "after:<step>" or
// "error:<step>". The step of the pipeline itself is "".
type RecordHook struct {
	events []string
}

func (h *RecordHook) Before(_ context.Context, step string, _ *codeupipe.Payload) {
	h.events = append(h.events, "before:"+step)
}

func (h *RecordHook) After(_ context.Context, step string, _ *codeupipe.Payload) {
	h.events = append(h.events, "after:"+step)
}

func (h *RecordHook) OnError(_ context.Context, step string, _ error, _ *codeupipe.Payload) {
	h.events = append(h.events, "error:"+step)
}
