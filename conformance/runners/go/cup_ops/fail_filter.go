package cup_ops

import (
	"context"
	"errors"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// FailFilter returns an error that carries message.
type FailFilter struct {
	Message string
}

func (f FailFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	return errors.New(f.Message)
}
