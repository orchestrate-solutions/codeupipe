//go:build ignore

// The acceptance case of AuditTap.
package main

import (
	"testing"

	"/audit_tap"
)

func TestAuditTap(t *testing.T) {
	if (&AuditTap{}) == nil {
		t.Fatal("Write the acceptance case for AuditTap.")
	}
	t.Fatal("Write the acceptance case for AuditTap.")
}
