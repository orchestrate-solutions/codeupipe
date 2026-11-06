package codeupipelint

import "context"

// DropExcludedFilter drops the files that match a glob of Exclude (CUP config and --exclude).
//
// TODO: not written yet. It finds nothing.
type DropExcludedFilter struct{}

func (DropExcludedFilter) Call(ctx context.Context, run *LintRun) error {
	return nil
}
