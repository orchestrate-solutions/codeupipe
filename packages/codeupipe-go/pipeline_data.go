package codeupipe

// PipelineData is what a pipeline can carry from step to step.
//
// Payload is the default: a map that any developer can read, and that every
// runtime of codeupipe has. A type of your own can take its place, such as
// the struct that your steps would use anyway:
//
//	type Order struct {
//		Price float64
//		Qty   float64
//		Bulk  bool
//	}
//
//	func (o *Order) Copy() *Order {
//		copied := *o
//		return &copied
//	}
//
//	pipeline := codeupipe.NewPipelineOf[*Order]()
//
// The Pipeline asks one thing of it, Copy, for the copy that a run works on.
// The Filters, Predicates, Taps and Hooks of that pipeline then take the
// type, and a step for another type does not compile.
//
// Lineage (Pipeline.Observe) is kept only by a type that also has
// Stamp(label string), as Payload has. For any other type it does nothing.
type PipelineData[P any] interface {
	Copy() P
}

// stamper is a type that keeps lineage.
type stamper interface {
	Stamp(label string)
}
