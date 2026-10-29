package codeupipe

import "context"

// FilterOf changes the data of a pipeline that carries P. Call changes the
// data in place. A failure is an error, and it stops the run.
type FilterOf[P any] interface {
	Call(ctx context.Context, payload P) error
}

// Filter changes the Payload. It is the only step that writes.
//
//	type MarkBulkFilter struct{}
//
//	func (MarkBulkFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
//		payload.Insert("bulk", true)
//		return nil
//	}
type Filter = FilterOf[*Payload]
