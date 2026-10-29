package codeupipe_test

// A pipeline over a type of your own. Payload is the default, a map that any
// developer can read; a struct can take its place. The Pipeline asks one
// thing of it, Copy, for the copy that a run works on. Lineage is kept only
// by a type that has Stamp(label); for any other type it does nothing.

import (
	"context"
	"errors"
	"math"
	"strconv"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

type Order struct {
	Price float64
	Qty   float64
	Bulk  bool
}

func (o *Order) Copy() *Order {
	copied := *o
	return &copied
}

type TracedOrder struct {
	Order
	Steps []string
}

func (o *TracedOrder) Copy() *TracedOrder {
	return &TracedOrder{Order: o.Order, Steps: append([]string{}, o.Steps...)}
}

func (o *TracedOrder) Stamp(label string) {
	o.Steps = append(o.Steps, label)
}

type OrderDiscountFilter struct{}

func (OrderDiscountFilter) Call(_ context.Context, order *Order) error {
	order.Price = math.Round(order.Price*90) / 100
	return nil
}

type OrderBulkFilter struct{}

func (OrderBulkFilter) Call(_ context.Context, order *Order) error {
	order.Bulk = true
	return nil
}

type RefuseFreeFilter struct{}

func (RefuseFreeFilter) Call(_ context.Context, order *Order) error {
	if order.Price <= 0 {
		return errors.New("an order must cost something")
	}
	return nil
}

type PassTracedFilter struct{}

func (PassTracedFilter) Call(context.Context, *TracedOrder) error {
	return nil
}

type BulkPredicate struct{}

func (BulkPredicate) Test(_ context.Context, order *Order) bool {
	return order.Qty >= 10
}

type SeePriceTap struct {
	seen []float64
}

func (t *SeePriceTap) Observe(_ context.Context, order *Order) error {
	t.seen = append(t.seen, order.Price)
	return nil
}

type RecordOrderHook struct {
	codeupipe.HookBaseOf[*Order]
	events []string
}

func (h *RecordOrderHook) Before(_ context.Context, step string, _ *Order) {
	h.events = append(h.events, "before:"+step)
}

func (h *RecordOrderHook) OnError(_ context.Context, step string, _ error, order *Order) {
	h.events = append(h.events, "error:"+step+":"+strconv.FormatFloat(order.Price, 'g', -1, 64))
}

type OrderPricingPipeline struct{}

func (OrderPricingPipeline) AddSteps(pipeline *codeupipe.PipelineOf[*Order]) {
	pipeline.AddFilter(OrderDiscountFilter{})
	pipeline.AddValve(BulkPredicate{}, OrderBulkFilter{})
}

func TestEveryPrimitiveTakesTheType(t *testing.T) {
	tap := &SeePriceTap{}
	hook := &RecordOrderHook{}
	pipeline := codeupipe.NewNamedPipelineOf[*Order](OrderPricingPipeline{})
	pipeline.AddTap(tap)
	pipeline.UseHook(hook)
	given := &Order{Price: 100, Qty: 12}
	out, err := pipeline.Run(context.Background(), given)
	same(t, err, nil)
	same(t, out, &Order{Price: 90, Qty: 12, Bulk: true})
	same(t, given, &Order{Price: 100, Qty: 12}) // the caller's value is not changed
	same(t, tap.seen, []float64{90})
	same(t, pipeline.State().Executed(), []string{"OrderDiscountFilter", "OrderBulkFilter", "SeePriceTap"})
	same(t, hook.events, []string{"before:", "before:OrderDiscountFilter", "before:OrderBulkFilter"})
	_, err = pipeline.Run(context.Background(), &Order{Price: 100, Qty: 2})
	same(t, err, nil)
	same(t, pipeline.State().Skipped(), []string{"OrderBulkFilter"})
}

func TestANestedPipelineTakesTheType(t *testing.T) {
	pipeline := codeupipe.NewPipelineOf[*Order]()
	pipeline.AddPipeline(codeupipe.NewNamedPipelineOf[*Order](OrderPricingPipeline{}))
	pipeline.AddFilter(RefuseFreeFilter{})
	out, err := pipeline.Run(context.Background(), &Order{Price: 50, Qty: 10})
	same(t, err, nil)
	same(t, out, &Order{Price: 45, Qty: 10, Bulk: true})
	same(t, pipeline.State().Executed(), []string{"OrderPricingPipeline", "RefuseFreeFilter"})
}

func TestAFailureIsTheSameAsWithAPayload(t *testing.T) {
	hook := &RecordOrderHook{}
	pipeline := codeupipe.NewPipelineOf[*Order]()
	pipeline.AddFilter(OrderDiscountFilter{})
	pipeline.AddFilter(RefuseFreeFilter{})
	pipeline.UseHook(hook)
	out, err := pipeline.Run(context.Background(), &Order{Price: 0, Qty: 1})
	same(t, out, (*Order)(nil))
	same(t, err.Error(), "an order must cost something")
	same(t, pipeline.State().Executed(), []string{"OrderDiscountFilter"})
	same(t, hook.events[len(hook.events)-2:], []string{"error:RefuseFreeFilter:0", "error::0"})
}

func TestLineageDoesNothingForATypeWithoutStamp(t *testing.T) {
	pipeline := codeupipe.NewNamedPipelineOf[*Order](OrderPricingPipeline{})
	pipeline.Observe(false, true)
	out, err := pipeline.Run(context.Background(), &Order{Price: 100, Qty: 12})
	same(t, err, nil)
	same(t, out, &Order{Price: 90, Qty: 12, Bulk: true})
	same(t, pipeline.State().Executed(), []string{"OrderDiscountFilter", "OrderBulkFilter"})
}

func TestLineageIsKeptByATypeWithStamp(t *testing.T) {
	pipeline := codeupipe.NewPipelineOf[*TracedOrder]()
	pipeline.AddFilter(PassTracedFilter{})
	pipeline.Observe(false, true)
	given := &TracedOrder{Order: Order{Price: 100, Qty: 12}}
	out, err := pipeline.Run(context.Background(), given)
	same(t, err, nil)
	same(t, out.Steps, []string{"PassTracedFilter"})
	same(t, given.Steps, []string(nil))
}

// MarkRanFilter is a Filter of a Payload.
type MarkRanFilter struct{}

func (MarkRanFilter) Call(_ context.Context, payload *codeupipe.Payload) error {
	payload.Insert("ran", true)
	return nil
}

func TestAPayloadPipelineIsStillTheDefault(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(MarkRanFilter{})
	same(t, run(t, pipeline, nil).ToDict(), map[string]any{"ran": true})
}

// A pipeline carries one type: a step for another type does not compile.
// TestWhatTheContractRefusesDoesNotCompile checks it.
