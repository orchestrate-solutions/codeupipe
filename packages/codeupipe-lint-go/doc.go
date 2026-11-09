// Package codeupipelint is a linter for Go code that uses codeupipe. It
// reads the source and does not run it.
//
// The linter is a codeupipe pipeline (LintPipeline) that carries a type of
// its own, *LintRun, in place of a Payload: a run holds syntax trees, which
// are not JSON-shaped values.
//
//	run, err := codeupipelint.LintPaths([]string{"."}, codeupipelint.LintOptions{})
//	fmt.Println(run.Report)
package codeupipelint
