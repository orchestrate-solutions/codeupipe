package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// MergeFilter merges a Payload of value into the Payload.
type MergeFilter struct {
	Value map[string]any
}

func (f MergeFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Merge(codeupipe.NewPayload(f.Value))
	return nil
}
