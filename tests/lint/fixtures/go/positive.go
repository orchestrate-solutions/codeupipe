// Anonymous steps the Go analyzer must flag (expect: comments name the rule).
package app

import cup "example.com/codeupipe"

type Named struct{}

func (Named) Call(p cup.Payload) (cup.Payload, error) { return p, nil }

func isOn(p cup.Payload) bool { return true }

var globalPred = func(p cup.Payload) bool { return true }

type FilterFunc func(cup.Payload) (cup.Payload, error)

func makeClosure(k string) FilterFunc {
	return func(p cup.Payload) (cup.Payload, error) { return p, nil }
}

func makeLocal() cup.Filter {
	type Local struct{ Named }
	return &Local{}
}

func build() *cup.Pipeline {
	type Local struct{ Named }
	type LocalTap struct{}

	p := cup.NewPipeline()
	p.AddFilter(FilterFunc(func(p cup.Payload) (cup.Payload, error) { return p, nil }), "inline") // expect: CUP-A001
	p.AddFilter(&Local{}, "local")                                                               // expect: CUP-A003
	p.AddFilter(Local{}, "local value")                                                          // expect: CUP-A003
	p.AddFilter(new(Local), "local new")                                                         // expect: CUP-A003
	p.AddTap(&LocalTap{}, "tap")                                                                 // expect: CUP-A003
	p.AddFilter(&struct{ Named }{}, "anonymous struct")                                          // expect: CUP-A004
	p.AddFilter(cup.NewValve("gate", &Named{}, func(p cup.Payload) bool { return true }), "g")   // expect: CUP-A001
	p.AddFilter(cup.NewValve("gate", &Local{}, isOn), "g2")                                      // expect: CUP-A003
	p.AddFilter(cup.NewValve("gate", &Named{}, globalPred), "g3")                                // expect: CUP-A001

	pred := func(p cup.Payload) bool { return true }
	v := cup.NewValve("gate", &Named{}, pred) // expect: CUP-A001
	p.AddFilter(v, "gate")

	loc := &Local{}
	p.AddFilter(loc, "bound local") // expect: CUP-A003

	p.AddFilter(makeClosure("x"), "closure") // expect: CUP-A001
	p.AddFilter(makeLocal(), "factory")      // expect: CUP-A003

	p.AddParallel([]cup.Filter{&Named{}, &Local{}}, "fan") // expect: CUP-A003

	child := cup.NewPipeline().AddFilter(&Named{}, "inner")
	p.AddPipeline(child, "child")                 // expect: CUP-A005
	p.AddPipeline(cup.NewPipeline(), "empty")      // expect: CUP-A005

	cup.NewPipeline().
		AddFilter(&Named{}, "a").
		AddFilter(&Local{}, "b") // expect: CUP-A003
	return p
}

func inClosure() {
	run := func() {
		type Hidden struct{ Named }
		cup.NewPipeline().AddFilter(Hidden{}, "hidden") // expect: CUP-A003
	}
	run()
}

// The conformance runner's shape: factories returning (step, error).
func predicate(key string) (func(cup.Payload) bool, error) {
	return func(p cup.Payload) bool { return p.Get(key) != nil }, nil
}

func buildTree(depth int) (*cup.Pipeline, error) {
	p := cup.NewPipeline()
	if depth > 0 {
		child, err := buildTree(depth - 1)
		if err != nil {
			return nil, err
		}
		p.AddPipeline(child, "child") // expect: CUP-A005
	}
	pred, _ := predicate("k")
	p.AddFilter(cup.NewValve("v", &Named{}, pred), "v") // expect: CUP-A001
	return p, nil
}
