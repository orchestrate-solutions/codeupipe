package main

import (
	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// Layout is "codeupipe add --layout": the command as a codeupipe pipeline
// (ADD.md, "Phase 2: a layout"). One step in each file of this directory.
//
// The Payload goes through eight Filters:
//
//  1. ParseLayoutArgumentsFilter  the arguments -> layout_path
//  2. ReadLayoutFilter            the file, as data
//  3. CheckLayoutFilter           the keys, and the shape of each
//  4. NameComponentsFilter        the names and the paths of phase 1
//  5. ResolveStepsFilter          the calls of each pipeline
//  6. RenderLayoutFilter          the text of the files
//  7. WriteLayoutFilter           the files that are not there yet
//  8. StalePipelinesFilter        a kept pipeline whose steps changed
//
// The whole layout is checked before a file is written: a step that cannot
// go on returns a Refusal, and the command writes nothing.
type Layout struct{}

// AddSteps adds the eight steps, in order.
func (Layout) AddSteps(pipeline *codeupipe.Pipeline) {
	pipeline.AddFilter(ParseLayoutArgumentsFilter{})
	pipeline.AddFilter(ReadLayoutFilter{})
	pipeline.AddFilter(CheckLayoutFilter{})
	pipeline.AddFilter(NameComponentsFilter{})
	pipeline.AddFilter(ResolveStepsFilter{})
	pipeline.AddFilter(RenderLayoutFilter{})
	pipeline.AddFilter(WriteLayoutFilter{})
	pipeline.AddFilter(StalePipelinesFilter{})
}
