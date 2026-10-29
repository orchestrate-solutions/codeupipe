package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// NoopTap does nothing.
type NoopTap struct{}

func (NoopTap) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	return nil
}
