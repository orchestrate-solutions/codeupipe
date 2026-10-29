//go:build ignore

// AuditTap: TODO: say what AuditTap does.
package main

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// AuditTap is a Tap: it reads nothing yet.
type AuditTap struct{}

// Observe does nothing.
func (AuditTap) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	return nil
}
