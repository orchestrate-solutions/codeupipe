// Add is "codeupipe add" for Go: the command that makes the files of a
// component (conformance/ADD.md). The command is a codeupipe pipeline: one
// step in each file of this directory. See Add.
package main

import (
	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// Add is "codeupipe add": the command as a codeupipe pipeline. One step in
// each file of this directory.
//
// The Payload goes through six Filters:
//
//  1. ParseArgumentsFilter  the arguments -> kind, name, directory, description
//  2. TypeNameFilter        kind and name -> DiscountFilter, discount_filter
//  3. PlanFilesFilter       the two paths, and the package of the component
//  4. RefuseExistingFilter  a file that exists stops the run (exit 1)
//  5. RenderFilesFilter     the text of the two files
//  6. WriteFilesFilter      the files, on disk
//
// A step that cannot go on returns a Refusal, which stops the run with the
// exit code of the contract, and the command writes nothing.
type Add struct{}

// AddSteps adds the six steps, in the order of the contract.
func (Add) AddSteps(pipeline *codeupipe.Pipeline) {
	pipeline.AddFilter(ParseArgumentsFilter{})
	pipeline.AddFilter(TypeNameFilter{})
	pipeline.AddFilter(PlanFilesFilter{})
	pipeline.AddFilter(RefuseExistingFilter{})
	pipeline.AddFilter(RenderFilesFilter{})
	pipeline.AddFilter(WriteFilesFilter{})
}

// Written gives the paths that a run made, component first, as main prints
// them.
func Written(out *codeupipe.Payload) []string {
	list, _ := out.Get("written").([]string)
	return list
}
