package codeupipelint

import "context"

// AnalyzePlainLogicFilter finds logic that is not in a primitive: CUP-I008, a warning.
//
// TODO: not written yet. It finds nothing.
type AnalyzePlainLogicFilter struct{}

func (AnalyzePlainLogicFilter) Call(ctx context.Context, run *LintRun) error {
	return nil
}
