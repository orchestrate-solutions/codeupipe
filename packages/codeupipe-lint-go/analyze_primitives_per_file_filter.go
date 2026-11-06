package codeupipelint

import "context"

// AnalyzePrimitivesPerFileFilter finds a second primitive at the top level of a file: CUP-I005.
//
// TODO: not written yet. It finds nothing.
type AnalyzePrimitivesPerFileFilter struct{}

func (AnalyzePrimitivesPerFileFilter) Call(ctx context.Context, run *LintRun) error {
	return nil
}
