// Step-identity probe cases, with describe(label, f) replaced by
// p.AddFilter(f, label): the probe's cases as lint fixtures.
package main

import (
	cup "example.com/codeupipe"

	"example.com/app/filters"
)

type FilterFunc func(map[string]any) map[string]any

func makeClosure(k string) FilterFunc {
	return func(p map[string]any) map[string]any { p[k] = 1; return p }
}

func makeLocalType() any {
	type Local struct{ n int }
	return Local{}
}

func main() {
	p := cup.NewPipeline()
	p.AddFilter(filters.Validate{}, "struct value")
	p.AddFilter(filters.Validate{}, "same struct again")
	p.AddFilter(filters.Normalize, "package function")
	p.AddFilter(func(p map[string]any) map[string]any { return p }, "func literal") // expect: CUP-A001
	p.AddFilter(makeClosure("x"), "closure")                                        // expect: CUP-A001
	p.AddFilter(makeLocalType(), "type defined in a function")                      // expect: CUP-A003
	p.AddFilter(struct{ A int }{}, "anonymous struct")                              // expect: CUP-A004
}
