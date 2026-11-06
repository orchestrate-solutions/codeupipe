package codeupipelint

import "context"

// AnalyzePayloadWritesFilter finds a Tap, a Predicate or a Hook that writes to its payload: CUP-I004.
//
// TODO: not written yet. It finds nothing.
type AnalyzePayloadWritesFilter struct{}

func (AnalyzePayloadWritesFilter) Call(ctx context.Context, run *LintRun) error {
	return nil
}
