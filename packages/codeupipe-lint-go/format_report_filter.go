package codeupipelint

import (
	"context"
	"fmt"
	"sort"
	"strings"
)

// FormatReportFilter gives the findings as sorted report lines, and the
// exit code.
//
// Reads Findings, Suppressed, Errors and Strict. Writes Findings (sorted),
// Report (text for stdout), ErrorReport (text for stderr), and ExitCode: 0
// no findings, 1 findings, 2 a path could not be read, so the check is not
// complete.
//
// A warning is in the report and is counted apart. It does not make the
// exit code 1, unless the run is strict.
type FormatReportFilter struct{}

func (FormatReportFilter) Call(ctx context.Context, run *LintRun) error {
	sort.SliceStable(run.Findings, func(i, j int) bool {
		a, b := run.Findings[i], run.Findings[j]
		if a.Path != b.Path {
			return a.Path < b.Path
		}
		if a.Line != b.Line {
			return a.Line < b.Line
		}
		if a.Col != b.Col {
			return a.Col < b.Col
		}
		return a.Rule < b.Rule
	})
	warnings := 0
	lines := make([]string, 0, len(run.Findings)+1)
	for _, finding := range run.Findings {
		if finding.Warning {
			warnings++
		}
		lines = append(lines, finding.Format())
	}
	real := len(run.Findings) - warnings
	summary := map[int]string{0: "No findings", 1: "1 finding"}[real]
	if real > 1 {
		summary = fmt.Sprintf("%d findings", real)
	}
	if len(run.Suppressed) > 0 {
		summary += fmt.Sprintf(" (%d suppressed)", len(run.Suppressed))
	}
	summary += "."
	if warnings == 1 {
		summary += " 1 warning."
	} else if warnings > 1 {
		summary += fmt.Sprintf(" %d warnings.", warnings)
	}
	run.Report = strings.Join(append(lines, summary), "\n")
	errors := make([]string, 0, len(run.Errors))
	for _, err := range run.Errors {
		errors = append(errors, "error: "+err)
	}
	run.ErrorReport = strings.Join(errors, "\n")
	switch {
	case len(run.Errors) > 0:
		run.ExitCode = 2
	case real > 0 || (warnings > 0 && run.Strict):
		run.ExitCode = 1
	default:
		run.ExitCode = 0
	}
	return nil
}
