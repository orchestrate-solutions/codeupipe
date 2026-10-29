package main

import "github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"

// PricingPipeline is a named pipeline: codeupipe.NewNamedPipeline(PricingPipeline{}).
type PricingPipeline struct{}

func (PricingPipeline) AddSteps(pipeline *codeupipe.Pipeline) {
	pipeline.AddFilter(DiscountFilter{Rate: 0.1})
	// MarkBulkFilter runs only when the predicate is true.
	pipeline.AddValve(AtLeastPredicate{Key: "qty", Minimum: 10}, MarkBulkFilter{})
	// A Tap only reads. If it fails, State records the error and the run goes on.
	pipeline.AddTap(AuditTap{})
}
