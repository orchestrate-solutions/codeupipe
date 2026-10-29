package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// CopyFilter inserts to = get(from), nil if missing.
type CopyFilter struct {
	From string
	To   string
}

func (f CopyFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert(f.To, payload.Get(f.From))
	return nil
}
