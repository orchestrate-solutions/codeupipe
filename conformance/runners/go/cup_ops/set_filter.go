package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// SetFilter inserts key = value.
type SetFilter struct {
	Key   string
	Value any
}

func (f SetFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert(f.Key, f.Value)
	return nil
}
