package codeupipe_test

import (
	"context"
	"testing"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// WrapFilter is a generic step: its label has no type arguments.
type WrapFilter[T any] struct{}

func (WrapFilter[T]) Call(context.Context, *codeupipe.Payload) error {
	return nil
}

func TestTheLabelIsTheNameOfTheType(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddTap(&SeeTap{})
	same(t, pipeline.Labels(), []string{"AddFilter", "SeeTap"})
}

func TestTheSecondUseOfATypeGetsANumber(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddFilter(&AddFilter{})
	pipeline.AddFilter(AddFilter{})
	same(t, pipeline.Labels(), []string{"AddFilter", "AddFilter#2", "AddFilter#3"})
}

func TestAValveHasTheLabelOfItsFilter(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.AddValve(IsOnPredicate{}, AddFilter{})
	same(t, pipeline.Labels(), []string{"AddFilter", "AddFilter#2"})
}

func TestANestedPipelineHasTheLabelOfItsType(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddPipeline(codeupipe.NewNamedPipeline(InnerPipeline{}))
	pipeline.AddPipeline(codeupipe.NewPipeline())
	same(t, pipeline.Labels(), []string{"InnerPipeline", "Pipeline"})
}

func TestTheLabelOfAGenericTypeHasNoTypeArguments(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(WrapFilter[AddFilter]{})
	same(t, pipeline.Labels(), []string{"WrapFilter"})
}

func TestATypeDeclaredInAFunctionWorks(t *testing.T) {
	type LocalFilter struct{ AddFilter }
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(LocalFilter{})
	same(t, pipeline.Labels(), []string{"LocalFilter"})
}

func TestAStepOfATypeWithNoNameHasTheLabelAnonymous(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(struct{ AddFilter }{})
	same(t, pipeline.Labels(), []string{"anonymous"})
}

func TestLabelsGivesANewListEachTime(t *testing.T) {
	pipeline := codeupipe.NewPipeline()
	pipeline.AddFilter(AddFilter{})
	pipeline.Labels()[0] = "x"
	same(t, pipeline.Labels(), []string{"AddFilter"})
}

// A value with no Call is not a Filter, and AddValve(filter, predicate) does
// not compile: those are checked by the compiler. A nil step compiles, and
// is refused when it is added.
func TestANilStepIsRefusedWhenItIsAdded(t *testing.T) {
	refused := func(add func(), message string) {
		t.Helper()
		defer func() {
			t.Helper()
			same(t, recover(), message)
		}()
		add()
	}
	pipeline := codeupipe.NewPipeline()
	refused(func() { pipeline.AddFilter(nil) },
		"codeupipe: AddFilter needs a Filter, a value with Call(ctx, payload). It was given nil")
	refused(func() { pipeline.AddValve(nil, AddFilter{}) },
		"codeupipe: AddValve needs a Predicate, a value with Test(ctx, payload). It was given nil")
	refused(func() { pipeline.AddValve(IsOnPredicate{}, nil) },
		"codeupipe: AddValve needs a Filter, a value with Call(ctx, payload). It was given nil")
	refused(func() { pipeline.AddTap(nil) },
		"codeupipe: AddTap needs a Tap, a value with Observe(ctx, payload). It was given nil")
	refused(func() { pipeline.AddPipeline(nil) },
		"codeupipe: AddPipeline needs a Pipeline. It was given nil")
	refused(func() { pipeline.UseHook(nil) },
		"codeupipe: UseHook needs a Hook, a value with Before, After and OnError. It was given nil")
	same(t, pipeline.Labels(), []string{})
}
