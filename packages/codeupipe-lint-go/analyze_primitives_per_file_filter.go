package codeupipelint

import (
	"context"
	"fmt"
)

// AnalyzePrimitivesPerFileFilter finds a second primitive at the top level of a file: CUP-I005.
//
// Flagged: each primitive in a file after the first one. Not checked: the
// files whose name ends in _test.go.
//
// Reads Sources. Writes Findings.
type AnalyzePrimitivesPerFileFilter struct{}

func (AnalyzePrimitivesPerFileFilter) Call(ctx context.Context, run *LintRun) error {
	for _, source := range run.Sources {
		if IsTestFile(source.Path) {
			continue
		}
		primitives := PrimitivesIn(source.File)
		if len(primitives) < 2 {
			continue
		}
		first := primitives[0]
		for _, other := range primitives[1:] {
			what := fmt.Sprintf("%s `%s` shares this file with %s `%s`",
				other.Kind.Name(), other.Name, first.Kind.Name(), first.Name)
			run.Findings = append(run.Findings, MakeFinding(source, other.Pos, OnePrimitivePerFile, what, 0))
		}
	}
	return nil
}
