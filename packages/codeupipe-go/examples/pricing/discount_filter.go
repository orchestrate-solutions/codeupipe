package main

import (
	"context"
	"math"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// DiscountFilter is a Filter. Its setting is a field.
type DiscountFilter struct {
	Rate float64
}

func (f DiscountFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	price, _ := payload.Get("price").(float64)
	payload.Insert("price", math.Round(price*(1-f.Rate)*100)/100)
	return nil
}
