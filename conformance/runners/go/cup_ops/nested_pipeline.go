package cup_ops

import "github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"

// NestedPipeline is a named pipeline type, for a pipeline that is a step of
// another. The runner adds the steps of the case after it is made.
type NestedPipeline struct{}

func (NestedPipeline) AddSteps(pipeline *codeupipe.Pipeline) {}
