package codeupipe

// NamedPipelineOf is a pipeline type of your own, for a pipeline that
// carries P. AddSteps adds its steps, and its label is the name of the type.
type NamedPipelineOf[P PipelineData[P]] interface {
	AddSteps(pipeline *PipelineOf[P])
}

// NamedPipeline is a pipeline type of your own. Nested in another pipeline,
// its label says what it is.
//
//	type PricingPipeline struct{}
//
//	func (PricingPipeline) AddSteps(pipeline *codeupipe.Pipeline) {
//		pipeline.AddFilter(DiscountFilter{Rate: 0.1})
//		pipeline.AddValve(AtLeastPredicate{Key: "qty", Minimum: 10}, MarkBulkFilter{})
//		pipeline.AddTap(AuditTap{})
//	}
//
//	pipeline := codeupipe.NewNamedPipeline(PricingPipeline{})
type NamedPipeline = NamedPipelineOf[*Payload]

// NewNamedPipeline gives the pipeline that named adds the steps of. Its
// label is the name of the type of named.
func NewNamedPipeline(named NamedPipeline) *Pipeline {
	return NewNamedPipelineOf[*Payload](named)
}

// NewNamedPipelineOf is NewNamedPipeline for a pipeline that carries P.
func NewNamedPipelineOf[P PipelineData[P]](named NamedPipelineOf[P]) *PipelineOf[P] {
	pipeline := NewPipelineOf[P]()
	pipeline.label = labelOf(named)
	named.AddSteps(pipeline)
	return pipeline
}
