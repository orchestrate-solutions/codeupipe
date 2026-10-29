package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// MutateFilter inserts key = value as a statement of its own. A Go Filter
// always changes the Payload in place, so this is the same as SetFilter; the
// case is kept so that every runtime runs it.
type MutateFilter struct {
	Key   string
	Value any
}

func (f MutateFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	payload.Insert(f.Key, f.Value)
	return nil
}
