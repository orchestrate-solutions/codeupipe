package codeupipelint

import (
	"context"
	"slices"
)

// DropDisabledFilter drops the findings of the rules that the project
// switched off, from those that are reported and from those that a comment
// allowed.
//
// Reads Disable. Writes Findings and Suppressed.
type DropDisabledFilter struct{}

func (DropDisabledFilter) Call(ctx context.Context, run *LintRun) error {
	off := func(finding Finding) bool { return slices.Contains(run.Disable, finding.Rule) }
	run.Findings = slices.DeleteFunc(run.Findings, off)
	run.Suppressed = slices.DeleteFunc(run.Suppressed, off)
	return nil
}
