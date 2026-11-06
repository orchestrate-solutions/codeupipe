package codeupipelint

import (
	"context"
	"slices"
	"strings"
)

// anonymousMarkers allow a CUP-A finding.
var anonymousMarkers = []string{"allow-anonymous"}

// invariantMarkers allow a CUP-I finding.
var invariantMarkers = []string{"allow-state-read", "allow-shared-file", "allow-name", "allow-plain"}

// ApplySuppressionsFilter drops the findings that a comment allows.
//
// "// cup: allow-anonymous" allows a CUP-A finding. "// cup: allow-state-read",
// "allow-shared-file", "allow-name" and "allow-plain" allow a CUP-I finding.
// The comment is on the line of the finding, on the line of the Add... call
// around it, or alone on the line directly above. Any text can follow the
// marker.
//
// Reads Findings and Sources. Writes Findings (kept), Suppressed (dropped),
// and UsedMarkers (each comment that allowed a finding).
type ApplySuppressionsFilter struct{}

func (ApplySuppressionsFilter) Call(ctx context.Context, run *LintRun) error {
	markers := map[string][]Marker{}
	for _, source := range run.Sources {
		markers[source.Path] = source.Markers
	}
	var kept []Finding
	for _, finding := range run.Findings {
		kinds := invariantMarkers
		if strings.HasPrefix(finding.Rule, "CUP-A") {
			kinds = anonymousMarkers
		}
		var places []int
		for _, marker := range markers[finding.Path] {
			at := marker.Line == finding.Line ||
				(finding.CallLine != 0 && marker.Line == finding.CallLine) ||
				(marker.Alone && marker.Line+1 == finding.Line)
			if at && slices.Contains(kinds, marker.Kind) {
				places = append(places, marker.Line)
			}
		}
		if len(places) == 0 {
			kept = append(kept, finding)
			continue
		}
		for _, line := range places {
			run.UsedMarkers = append(run.UsedMarkers, MarkerAt{Path: finding.Path, Line: line})
		}
		run.Suppressed = append(run.Suppressed, finding)
	}
	run.Findings = kept
	return nil
}
