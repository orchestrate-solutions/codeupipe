// Named steps the Go analyzer must NOT flag.
package app

import cup "example.com/codeupipe"

type Named struct{ key string }

func (Named) Call(p cup.Payload) (cup.Payload, error) { return p, nil }

type Audit struct{}

func (Audit) Observe(p cup.Payload) {}

type Onboarding struct{ *cup.Pipeline }

func NewOnboarding() *Onboarding { return &Onboarding{cup.NewPipeline().AddFilter(&Named{}, "n")} }

func isOn(p cup.Payload) bool { return true }

func makeNamed() cup.Filter { return &Named{key: "k"} }

func build(steps []cup.Filter, pred func(cup.Payload) bool) *cup.Pipeline {
	p := cup.NewPipeline() // a plain pipeline at the top level is fine
	p.AddFilter(&Named{key: "a"}, "a")
	p.AddFilter(Named{}, "b")
	p.AddTap(&Audit{}, "audit")
	p.AddFilter(cup.NewValve("gate", &Named{}, isOn), "gate")
	p.AddFilter(cup.NewValve("gate", &Named{}, pred), "param pred")
	p.AddPipeline(NewOnboarding(), "onboarding")
	p.AddParallel([]cup.Filter{&Named{}, &Named{}}, "fan")
	p.AddFilter(makeNamed(), "factory")
	for _, s := range steps {
		p.AddFilter(s, "loop")
	}
	sorter := func(a, b int) bool { return a < b } // a func literal that is not a step
	_ = sorter
	return p
}
