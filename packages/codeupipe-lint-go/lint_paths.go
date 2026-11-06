package codeupipelint

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// LintOptions say how a run is done: the files that are left out, the rules
// that are off, and whether a warning fails the run.
type LintOptions struct {
	Exclude []string
	Disable []string
	Strict  bool
}

// LintPaths runs the linter over paths (files or directories). The run that
// comes back holds Findings, Suppressed, Errors, Report, ErrorReport and
// ExitCode.
func LintPaths(paths []string, options LintOptions) (*LintRun, error) {
	pipeline := codeupipe.NewNamedPipelineOf[*LintRun](LintPipeline{})
	return pipeline.Run(context.Background(), &LintRun{
		Paths:   paths,
		Exclude: options.Exclude,
		Disable: options.Disable,
		Strict:  options.Strict,
	})
}
