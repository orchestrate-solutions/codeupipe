package codeupipelint

import "github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"

// LintPipeline is the linter, as a codeupipe pipeline:
// codeupipe.NewNamedPipelineOf[*LintRun](LintPipeline{}).
type LintPipeline struct{}

func (LintPipeline) AddSteps(pipeline *codeupipe.PipelineOf[*LintRun]) {
	pipeline.AddFilter(CollectFilesFilter{})             // paths to files
	pipeline.AddFilter(DropExcludedFilter{})             // --exclude, lint.exclude
	pipeline.AddFilter(ParseFilesFilter{})               // files to syntax trees (CUP-I000)
	pipeline.AddFilter(AnalyzeStepsFilter{})             // CUP-A001, A003, A005, A008
	pipeline.AddFilter(AnalyzeStateReadsFilter{})        // CUP-I003
	pipeline.AddFilter(AnalyzePayloadWritesFilter{})     // CUP-I004
	pipeline.AddFilter(AnalyzePrimitivesPerFileFilter{}) // CUP-I005
	pipeline.AddFilter(AnalyzePrimitiveNamesFilter{})    // CUP-I006, I007
	pipeline.AddFilter(AnalyzePlainLogicFilter{})        // CUP-I008, a warning
	pipeline.AddFilter(ApplySuppressionsFilter{})
	pipeline.AddFilter(AnalyzeStaleMarkersFilter{}) // CUP-I009, a warning
	pipeline.AddFilter(DropDisabledFilter{})        // last, so that a comment for a rule that is off is not stale
	pipeline.AddFilter(FormatReportFilter{})
}
