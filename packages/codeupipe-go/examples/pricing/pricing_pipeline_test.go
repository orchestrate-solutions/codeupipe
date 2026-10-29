package main

import (
	"context"
	"reflect"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

func same(t *testing.T, got, want any) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %#v, want %#v", got, want)
	}
}

func TestALargeOrderGetsTheDiscountAndTheBulkMark(t *testing.T) {
	pipeline := codeupipe.NewNamedPipeline(PricingPipeline{})
	out, err := pipeline.Run(context.Background(), codeupipe.NewPayload(map[string]any{"price": 100, "qty": 12}))
	same(t, err, nil)
	same(t, out.ToDict(), map[string]any{"price": 90.0, "qty": 12.0, "bulk": true})
	same(t, pipeline.State().Executed(), []string{"DiscountFilter", "MarkBulkFilter", "AuditTap"})
	same(t, pipeline.State().Errors(), []codeupipe.StepFailure{})
}

func TestASmallOrderGetsTheDiscountOnly(t *testing.T) {
	pipeline := codeupipe.NewNamedPipeline(PricingPipeline{})
	out, err := pipeline.Run(context.Background(), codeupipe.NewPayload(map[string]any{"price": 100, "qty": 2}))
	same(t, err, nil)
	same(t, out.ToDict(), map[string]any{"price": 90.0, "qty": 2.0})
	same(t, pipeline.State().Skipped(), []string{"MarkBulkFilter"})
}

func TestTheTapReadsThePayload(t *testing.T) {
	err := AuditTap{}.Observe(context.Background(), codeupipe.NewPayload(map[string]any{"price": 90}))
	same(t, err, nil)
}
