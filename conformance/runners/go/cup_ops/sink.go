// Package cup_ops has the steps of the cases: one type for each step, with
// the names that the TypeScript and Rust runners use, so that the labels are
// the same.
package cup_ops

import (
	"context"
	"errors"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// Where the steps of the runner record what they see, and the function that
// runs the pipeline of a case again. The runner plays one case at a time, in
// one goroutine, and empties these before each case.
var (
	taps        []any
	runAgain    func(ctx context.Context, input map[string]any) error
	innerStates []*codeupipe.State
)

// Record adds a value to the tap log.
func Record(value any) {
	taps = append(taps, value)
}

// TakeTaps gives what was recorded since the last call, and empties the log.
func TakeTaps() []any {
	recorded := append([]any{}, taps...)
	taps = nil
	return recorded
}

// SetRunAgain sets how the RunAgainFilter of this case runs its pipeline
// again. nil removes it.
func SetRunAgain(run func(ctx context.Context, input map[string]any) error) {
	runAgain = run
}

// RunAgain runs the pipeline of the case again, with input and a new State.
func RunAgain(ctx context.Context, input map[string]any) error {
	if runAgain == nil {
		return errors.New("no pipeline to run again")
	}
	return runAgain(ctx, input)
}

// KeepInnerState keeps the State of a run that a RunAgainFilter started.
func KeepInnerState(state *codeupipe.State) {
	innerStates = append(innerStates, state)
}

// TakeInnerStates gives the States kept since the last call, and empties
// the list.
func TakeInnerStates() []*codeupipe.State {
	kept := innerStates
	innerStates = nil
	return kept
}
