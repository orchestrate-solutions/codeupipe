package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// HasFilter inserts to = has(key).
type HasFilter struct {
	Key string
	To  string
}

func (f HasFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert(f.To, payload.Has(f.Key))
	return nil
}
