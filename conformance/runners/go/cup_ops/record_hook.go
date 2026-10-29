package cup_ops

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// RecordHook records "before:<step>", "after:<step>" and "error:<step>".
// Events of the pipeline itself have an empty step.
type RecordHook struct {
	Events *[]string
}

func (h RecordHook) Before(ctx context.Context, step string, payload *codeupipe.Payload) {
	*h.Events = append(*h.Events, "before:"+step)
}

func (h RecordHook) After(ctx context.Context, step string, payload *codeupipe.Payload) {
	*h.Events = append(*h.Events, "after:"+step)
}

func (h RecordHook) OnError(ctx context.Context, step string, err error, payload *codeupipe.Payload) {
	*h.Events = append(*h.Events, "error:"+step)
}
