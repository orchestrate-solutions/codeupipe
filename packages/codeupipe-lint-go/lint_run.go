package codeupipelint

import "slices"

// LintRun is what the lint pipeline carries from step to step: the input of
// a run, and what each step adds.
type LintRun struct {
	// Paths are the files or directories to check.
	Paths []string
	// Exclude holds globs matched against the path of each file; a match is
	// not checked.
	Exclude []string
	// Disable holds the rule ids that are switched off.
	Disable []string
	// Strict makes a warning fail the run too.
	Strict bool
	// Files are the Go files under Paths (CollectFilesFilter).
	Files []string
	// Sources are the files that parse (ParseFilesFilter).
	Sources []Source
	// Findings are the findings that are reported.
	Findings []Finding
	// Suppressed are the findings that a comment allowed
	// (ApplySuppressionsFilter).
	Suppressed []Finding
	// UsedMarkers holds each comment that allowed a finding.
	UsedMarkers []MarkerAt
	// Errors holds each path that could not be read: the check is not
	// complete.
	Errors []string
	// Report is the text for stdout (FormatReportFilter).
	Report string
	// ErrorReport is the text for stderr.
	ErrorReport string
	// ExitCode is 0 for no findings, 1 for findings, 2 when a path could not
	// be read.
	ExitCode int
}

// MarkerAt is the place of a comment: a path and a line.
type MarkerAt struct {
	Path string
	Line int
}

// Copy gives the run that a pipeline works on. Each list is copied, so that
// a step that appends does not write into the caller's run.
func (r *LintRun) Copy() *LintRun {
	copied := *r
	copied.Paths = slices.Clone(r.Paths)
	copied.Exclude = slices.Clone(r.Exclude)
	copied.Disable = slices.Clone(r.Disable)
	copied.Files = slices.Clone(r.Files)
	copied.Sources = slices.Clone(r.Sources)
	copied.Findings = slices.Clone(r.Findings)
	copied.Suppressed = slices.Clone(r.Suppressed)
	copied.UsedMarkers = slices.Clone(r.UsedMarkers)
	copied.Errors = slices.Clone(r.Errors)
	return &copied
}
