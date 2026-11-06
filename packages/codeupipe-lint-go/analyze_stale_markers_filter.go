package codeupipelint

import "context"

// AnalyzeStaleMarkersFilter finds a cup: allow-... comment that allowed no finding: CUP-I009, a warning.
//
// TODO: not written yet. It finds nothing.
type AnalyzeStaleMarkersFilter struct{}

func (AnalyzeStaleMarkersFilter) Call(ctx context.Context, run *LintRun) error {
	return nil
}
