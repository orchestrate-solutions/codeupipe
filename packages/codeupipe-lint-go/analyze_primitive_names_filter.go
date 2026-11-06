package codeupipelint

import "context"

// AnalyzePrimitiveNamesFilter finds a primitive whose file name or type name does not fit: CUP-I006, I007.
//
// TODO: not written yet. It finds nothing.
type AnalyzePrimitiveNamesFilter struct{}

func (AnalyzePrimitiveNamesFilter) Call(ctx context.Context, run *LintRun) error {
	return nil
}
