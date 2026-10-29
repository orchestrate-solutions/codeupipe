package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// RemoveFilter removes key.
type RemoveFilter struct {
	Key string
}

func (f RemoveFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Remove(f.Key)
	return nil
}
