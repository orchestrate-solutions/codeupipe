package codeupipelint

import "context"

// AnalyzeStateReadsFilter finds a Filter or a Predicate that reads the State of a pipeline: CUP-I003.
//
// TODO: not written yet. It finds nothing.
type AnalyzeStateReadsFilter struct{}

func (AnalyzeStateReadsFilter) Call(ctx context.Context, run *LintRun) error {
	return nil
}
