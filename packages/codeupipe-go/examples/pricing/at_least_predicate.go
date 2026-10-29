package main

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// AtLeastPredicate is a Predicate: it asks a yes-or-no question and changes
// nothing. Its settings are fields.
type AtLeastPredicate struct {
	Key     string
	Minimum float64
}

func (q AtLeastPredicate) Test(ctx context.Context, payload *codeupipe.Payload) bool {
	value, _ := payload.Get(q.Key).(float64)
	return value >= q.Minimum
}
