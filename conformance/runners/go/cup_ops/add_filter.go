package cup_ops

import (
	"context"
	"fmt"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// AddFilter inserts key = get(key, 0) + by. A value that is there and is not
// a number is an error, as in Python.
type AddFilter struct {
	Key string
	By  float64
}

func (f AddFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	n := 0.0
	if payload.Has(f.Key) {
		value, ok := payload.Get(f.Key).(float64)
		if !ok {
			return fmt.Errorf("'%s' is not a number: %v", f.Key, payload.Get(f.Key))
		}
		n = value
	}
	payload.Insert(f.Key, n+f.By)
	return nil
}
