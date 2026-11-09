package codeupipelint

import "context"

// AnalyzeStaleMarkersFilter finds a cup: allow-... comment that allowed no finding: CUP-I009, a warning.
//
// A comment stays when the code that it was for is gone or has moved, or
// when its kind has a spelling error. Each comment that is not in UsedMarkers
// is a finding, at the line and the column of the comment.
//
// Reads Sources and UsedMarkers (from ApplySuppressionsFilter). Writes Findings.
type AnalyzeStaleMarkersFilter struct{}

func (f AnalyzeStaleMarkersFilter) Call(ctx context.Context, run *LintRun) error {
	used := map[MarkerAt]bool{}
	for _, at := range run.UsedMarkers {
		used[at] = true
	}
	for _, source := range run.Sources {
		for _, marker := range source.Markers {
			at := MarkerAt{Path: source.Path, Line: marker.Line}
			if used[at] {
				continue
			}
			run.Findings = append(run.Findings, f.finding(source, marker))
		}
	}
	return nil
}

// finding gives a CUP-I009 finding at the comment of marker. A marker has a
// line and a column, not a token.Pos, so the finding is made here.
func (AnalyzeStaleMarkersFilter) finding(source Source, marker Marker) Finding {
	rule, _ := RuleOf(MarkerAllowsNothing)
	return Finding{
		Path:    source.Path,
		Line:    marker.Line,
		Col:     marker.Col,
		Rule:    rule.ID,
		Slug:    rule.Slug,
		Message: "The comment `cup: " + marker.Kind + "` allows nothing. " + rule.Fix,
		Warning: rule.Warning,
	}
}
