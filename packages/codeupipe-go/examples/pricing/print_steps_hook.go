package main

import (
	"context"
	"fmt"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// PrintStepsHook is a Hook: it sees the lifecycle. step is the label of the
// step, which is the name of its type. It is "" for the pipeline itself.
// HookBase gives the methods that it does not write.
type PrintStepsHook struct {
	codeupipe.HookBase
}

func (PrintStepsHook) Before(ctx context.Context, step string, payload *codeupipe.Payload) {
	if step != "" {
		fmt.Println(" ", step)
	}
}
