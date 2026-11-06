package codeupipelint

import "context"

// AnalyzeStepsFilter finds the steps that are not named types: CUP-A001, A003, A005, A008.
//
// TODO: not written yet. It finds nothing.
type AnalyzeStepsFilter struct{}

func (AnalyzeStepsFilter) Call(ctx context.Context, run *LintRun) error {
	return nil
}
