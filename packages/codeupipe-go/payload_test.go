package codeupipe_test

import (
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

func TestTheMapThatTheCallerGivesIsCopied(t *testing.T) {
	data := map[string]any{"a": 1.0}
	payload := codeupipe.NewPayload(data)
	payload.Insert("b", 2.0)
	same(t, data, map[string]any{"a": 1.0})
	same(t, payload.ToDict(), map[string]any{"a": 1.0, "b": 2.0})
}

func TestAnEmptyPayloadHasNoKeys(t *testing.T) {
	same(t, codeupipe.NewPayload(nil).ToDict(), map[string]any{})
}

func TestGetGivesTheValueOrNil(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"a": 1.0, "n": nil})
	same(t, payload.Get("a"), 1.0)
	same(t, payload.Get("missing"), nil)
	same(t, payload.Get("n"), nil)
}

func TestADefaultIsATypeAssertion(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"price": 90.0, "name": "Ada"})
	price, ok := payload.Get("price").(float64)
	same(t, []any{price, ok}, []any{90.0, true})
	qty, ok := payload.Get("qty").(float64) // absent
	same(t, []any{qty, ok}, []any{0.0, false})
	count, ok := payload.Get("name").(float64) // not a number
	same(t, []any{count, ok}, []any{0.0, false})
}

func TestHasIsTrueForAKeyWithANilValue(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"n": nil})
	same(t, payload.Has("n"), true)
	same(t, payload.Has("missing"), false)
}

func TestInsertRemoveMergeAndWithTraceChangeThePayloadAndReturnIt(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"a": 1.0})
	same(t, payload.Insert("b", 2.0) == payload, true)
	same(t, payload.Remove("a") == payload, true)
	same(t, payload.Merge(codeupipe.NewPayload(map[string]any{"c": 3.0})) == payload, true)
	same(t, payload.WithTrace("t-1") == payload, true)
	same(t, payload.ToDict(), map[string]any{"b": 2.0, "c": 3.0})
	same(t, payload.TraceID(), "t-1")
}

func TestWritesChain(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"a": 1.0})
	payload.Insert("b", 2.0).Remove("a").Insert("c", 3.0)
	same(t, payload.ToDict(), map[string]any{"b": 2.0, "c": 3.0})
}

func TestRemoveOfAKeyThatIsNotThereDoesNothing(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"a": 1.0}).Remove("zz")
	same(t, payload.ToDict(), map[string]any{"a": 1.0})
}

func TestInAMergeTheOtherPayloadWins(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"a": 1.0, "b": 1.0})
	payload.Merge(codeupipe.NewPayload(map[string]any{"b": 2.0}))
	same(t, payload.ToDict(), map[string]any{"a": 1.0, "b": 2.0})
}

func TestAMergeKeepsTheTraceIDItHasAndTakesOneWhenItHasNone(t *testing.T) {
	other := codeupipe.NewPayload(nil).WithTrace("other")
	same(t, codeupipe.NewPayload(nil).WithTrace("mine").Merge(other).TraceID(), "mine")
	same(t, codeupipe.NewPayload(nil).Merge(other).TraceID(), "other")
}

func TestCopyGivesASeparatePayloadWithTheSameContents(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"a": 1.0}).WithTrace("t-1")
	copied := payload.Copy()
	copied.Insert("a", 2.0)
	same(t, payload.Get("a"), 1.0)
	same(t, copied.TraceID(), "t-1")
}

func TestCopyIsShallowTheTwoPayloadsShareTheirValues(t *testing.T) {
	list := []any{1.0}
	payload := codeupipe.NewPayload(map[string]any{"list": list})
	shared := payload.Copy().Get("list").([]any)
	same(t, &shared[0] == &list[0], true)
}

func TestToDictGivesANewMapEachTime(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"a": 1.0})
	payload.ToDict()["a"] = 2.0
	same(t, payload.Get("a"), 1.0)
}

func TestTheTraceIDIsEmptyUntilItIsSetAndTheLineageStartsEmpty(t *testing.T) {
	payload := codeupipe.NewPayload(nil)
	same(t, payload.TraceID(), "")
	same(t, payload.Lineage(), []string{})
}

func TestTheLineageIsACopy(t *testing.T) {
	payload := codeupipe.NewPayload(nil)
	payload.Stamp("AFilter")
	payload.Lineage()[0] = "changed"
	same(t, payload.Lineage(), []string{"AFilter"})
}

// D1: one number type. Go's other number types become float64, so a value
// that is inserted as 12 is read back with .(float64).
func TestANumberIsAFloat64(t *testing.T) {
	payload := codeupipe.NewPayload(map[string]any{"given": 7})
	payload.Insert("int", 12).Insert("int64", int64(-3)).Insert("uint8", uint8(200)).Insert("float32", float32(0.5))
	same(t, payload.ToDict(), map[string]any{
		"given": 7.0, "int": 12.0, "int64": -3.0, "uint8": 200.0, "float32": 0.5,
	})
}

func TestAListOrAMapIsKeptAsItIsGiven(t *testing.T) {
	payload := codeupipe.NewPayload(nil).Insert("list", []any{1}).Insert("ints", []int{1})
	same(t, payload.Get("list"), []any{1})
	same(t, payload.Get("ints"), []int{1})
}

func TestTheZeroPayloadCanBeWritten(t *testing.T) {
	var payload codeupipe.Payload
	payload.Insert("a", 1.0)
	same(t, payload.ToDict(), map[string]any{"a": 1.0})
	same(t, (&codeupipe.Payload{}).Has("a"), false)
	same(t, (&codeupipe.Payload{}).Copy().Insert("a", 1.0).ToDict(), map[string]any{"a": 1.0})
}
