package codeupipe

import "fmt"

// Valve is conditional flow control — gates a Filter with a predicate.
// The inner filter only executes when the predicate returns true.
// Otherwise the payload passes through unchanged.
//
// Valve implements the Filter interface.
//
// See also: TypeScript, Python, Rust, C# implementations.
type Valve struct {
	// PredicateSymbol is the predicate's identity (detail: a Valve is
	// identified by its inner filter, conformance/API.md).
	PredicateSymbol string
	inner           Filter
	predicate       Predicate
	LastSkipped     bool
}

// NewValve creates a Valve wrapping a filter with a predicate object,
// identified by its type (conformance/API.md, "Valve").
func NewValve(inner Filter, predicate Predicate) *Valve {
	return &Valve{
		PredicateSymbol: identify(predicate, "Valve predicate"),
		inner:           inner,
		predicate:       predicate,
	}
}

// Call evaluates the predicate and either runs or skips the inner filter.
func (v *Valve) Call(payload Payload) (Payload, error) {
	if v.predicate.Test(payload) {
		v.LastSkipped = false
		return v.inner.Call(payload)
	}
	v.LastSkipped = true
	return payload, nil
}

// String returns a human-readable representation.
func (v *Valve) String() string {
	return fmt.Sprintf("Valve(%s, %s)", identify(v.inner, "Filter"), v.PredicateSymbol)
}
