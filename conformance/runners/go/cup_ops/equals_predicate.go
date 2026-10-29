package cup_ops

import (
	"context"
	"reflect"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// EqualsPredicate is true when get(key) == value, by content. A missing key
// is nil. A number is never equal to a bool: they are values of two types.
type EqualsPredicate struct {
	Key   string
	Value any
}

func (q EqualsPredicate) Test(ctx context.Context, payload *codeupipe.Payload) bool {
	return reflect.DeepEqual(payload.Get(q.Key), q.Value)
}
