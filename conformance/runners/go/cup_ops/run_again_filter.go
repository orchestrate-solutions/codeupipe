package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// RunAgainFilter runs the pipeline that it is in one more time, with Input
// and a new State, when get("inner") is not true. How a pipeline is run
// again depends on the target, so the runner gives that as a function
// (SetRunAgain). Then the payload goes on with no change.
type RunAgainFilter struct {
	Input map[string]any
}

func (f RunAgainFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	if payload.Get("inner") == true {
		return nil
	}
	return RunAgain(ctx, f.Input)
}
