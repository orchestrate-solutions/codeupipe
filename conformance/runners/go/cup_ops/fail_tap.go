package cup_ops

import (
	"context"
	"errors"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// FailTap returns an error that carries message.
type FailTap struct {
	Message string
}

func (t FailTap) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	return errors.New(t.Message)
}
