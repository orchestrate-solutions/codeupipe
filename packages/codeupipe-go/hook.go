package codeupipe

import "context"

// HookOf sees the lifecycle of a run of a pipeline that carries P. It reads
// the data and does not write to it.
//
// step is the label of the step, or "" for the pipeline itself. On success:
// Before(""), then Before and After for each Filter or Valve, then
// After(""). On a Filter failure: OnError for the step, then OnError(""),
// and no After. Taps get no events.
type HookOf[P any] interface {
	Before(ctx context.Context, step string, payload P)
	After(ctx context.Context, step string, payload P)
	OnError(ctx context.Context, step string, err error, payload P)
}

// Hook sees the lifecycle of a run of a pipeline that carries a Payload.
type Hook = HookOf[*Payload]

// HookBaseOf has the three methods of a Hook, and they do nothing. Embed it,
// and write only the methods that you need.
type HookBaseOf[P any] struct{}

// Before does nothing.
func (HookBaseOf[P]) Before(context.Context, string, P) {}

// After does nothing.
func (HookBaseOf[P]) After(context.Context, string, P) {}

// OnError does nothing.
func (HookBaseOf[P]) OnError(context.Context, string, error, P) {}

// HookBase is HookBaseOf for a pipeline that carries a Payload.
//
//	type PrintStepsHook struct{ codeupipe.HookBase }
//
//	func (PrintStepsHook) Before(ctx context.Context, step string, payload *codeupipe.Payload) {
//		fmt.Println(step)
//	}
type HookBase = HookBaseOf[*Payload]
