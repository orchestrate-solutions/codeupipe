package codeupipe

import "context"

// PredicateOf asks a yes-or-no question about the data of a pipeline that
// carries P. It reads the data and does not write to it.
type PredicateOf[P any] interface {
	Test(ctx context.Context, payload P) bool
}

// Predicate asks a yes-or-no question about the Payload. Its settings (a
// threshold, a flag) are fields of the value, and one Predicate can be used
// in many Valves.
//
//	type AtLeastPredicate struct {
//		Key     string
//		Minimum float64
//	}
//
//	func (q AtLeastPredicate) Test(ctx context.Context, payload *codeupipe.Payload) bool {
//		value, _ := payload.Get(q.Key).(float64)
//		return value >= q.Minimum
//	}
type Predicate = PredicateOf[*Payload]
