package codeupipe

// Predicate is a Valve's condition (conformance/API.md, "Valve"): a named
// type with Test, identified by its type like a step, with any
// configuration in its fields:
//
//	type atLeast struct{ n int }
//	func (a atLeast) Test(p Payload) bool { ... }
//
// A plain function is not a Predicate (a compile error). A func adapter
// type implementing Test is identified by the function it wraps, so a
// closure is still refused.
type Predicate interface {
	Test(payload Payload) bool
}
