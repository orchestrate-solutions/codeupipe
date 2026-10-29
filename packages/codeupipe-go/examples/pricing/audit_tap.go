package main

import (
	"context"
	"fmt"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// AuditTap is a Tap: it reads the Payload and changes nothing. If it fails,
// State records the error and the run goes on.
type AuditTap struct{}

func (AuditTap) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	fmt.Println("audit:", payload.ToDict())
	return nil
}
