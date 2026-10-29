package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// TruthyPredicate is true when get(key) is truthy, as in Python: nil, false,
// 0, "" and an empty list or map are false. A missing key is false.
type TruthyPredicate struct {
	Key string
}

func (q TruthyPredicate) Test(ctx context.Context, payload *codeupipe.Payload) bool {
	switch value := payload.Get(q.Key).(type) {
	case nil:
		return false
	case bool:
		return value
	case float64:
		return value != 0
	case string:
		return value != ""
	case []any:
		return len(value) > 0
	case map[string]any:
		return len(value) > 0
	}
	return true
}
