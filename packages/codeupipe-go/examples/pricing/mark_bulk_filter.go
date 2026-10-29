package main

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// MarkBulkFilter is a Filter.
type MarkBulkFilter struct{}

func (MarkBulkFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert("bulk", true)
	return nil
}
