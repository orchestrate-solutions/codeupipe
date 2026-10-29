package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// RecordTap adds get(key) to the tap log of the runner.
type RecordTap struct {
	Key string
}

func (t RecordTap) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	Record(payload.Get(t.Key))
	return nil
}
