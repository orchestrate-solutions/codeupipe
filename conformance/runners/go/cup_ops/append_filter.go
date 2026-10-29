package cup_ops

import (
	"context"
	"fmt"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// AppendFilter inserts key = a copy of get(key), or of an empty list, with
// value added. The list that is there is not changed.
type AppendFilter struct {
	Key   string
	Value any
}

func (f AppendFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	var list []any
	switch items := payload.Get(f.Key).(type) {
	case nil:
	case []any:
		list = append(list, items...)
	default:
		return fmt.Errorf("'%s' is not a list: %v", f.Key, items)
	}
	payload.Insert(f.Key, append(list, f.Value))
	return nil
}
