package codeupipe

import (
	"errors"
	"reflect"
	"regexp"
	"strings"
	"testing"
)

// Step identity (conformance/API.md): a step is identified by its filter's
// fully qualified symbol, #n from its second use; no names.

const here = "github.com/codeuchain/codeupipe-core/codeupipe."

type incFilter struct{}

func (incFilter) Call(p Payload) (Payload, error) {
	n, _ := p.Get("n").(int)
	return p.Insert("n", n+1), nil
}

type boomFilter struct{}

func (boomFilter) Call(p Payload) (Payload, error) { return p, errors.New("boom") }

type auditTap struct{}

func (auditTap) Observe(Payload) {}

// onboarding is a named pipeline type: the Go equivalent of a Pipeline
// subclass is a named struct embedding *Pipeline.
type onboarding struct{ *Pipeline }

func newOnboarding() onboarding { return onboarding{NewPipeline().AddFilter(incFilter{})} }

// isOn is a predicate object: a named type with Test, identified by its type.
type isOn struct{}

func (isOn) Test(p Payload) bool { on, _ := p.Get("on").(bool); return on }

// atLeast is a configurable predicate: its setting lives on the value.
type atLeast struct{ n int }

func (a atLeast) Test(p Payload) bool { n, _ := p.Get("n").(int); return n >= a.n }

// predFunc adapts a function to Predicate; the wrapped function is then the
// identity, so a closure is still refused.
type predFunc func(Payload) bool

func (f predFunc) Test(p Payload) bool { return f(p) }

type recHook struct{ events []string }

func (h *recHook) Before(s string, _ Payload)           { h.events = append(h.events, "before:"+s) }
func (h *recHook) After(s string, _ Payload)            { h.events = append(h.events, "after:"+s) }
func (h *recHook) OnError(s string, _ error, _ Payload) { h.events = append(h.events, "error:"+s) }

func TestIdentityIsTheQualifiedSymbol(t *testing.T) {
	p := NewPipeline().AddFilter(incFilter{})
	if _, err := p.Run(NewPayload(nil)); err != nil {
		t.Fatal(err)
	}
	if got := p.State().Executed; !reflect.DeepEqual(got, []string{here + "incFilter"}) {
		t.Fatalf("executed = %v", got)
	}
}

func TestPointerAndValueFiltersShareIdentity(t *testing.T) {
	p := NewPipeline().AddFilter(incFilter{}).AddFilter(&incFilter{})
	want := []string{here + "incFilter", here + "incFilter#2"}
	if got := p.Identities(); !reflect.DeepEqual(got, want) {
		t.Fatalf("identities = %v, want %v", got, want)
	}
}

func TestTapsAndHooks(t *testing.T) {
	h := &recHook{}
	p := NewPipeline().AddFilter(incFilter{}).AddTap(auditTap{}).AddFilter(boomFilter{}).UseHook(h)
	if _, err := p.Run(NewPayload(nil)); err == nil {
		t.Fatal("expected boom")
	}
	want := []string{"before:", "before:" + here + "incFilter", "after:" + here + "incFilter",
		"before:" + here + "boomFilter", "error:" + here + "boomFilter", "error:"}
	if !reflect.DeepEqual(h.events, want) {
		t.Fatalf("hooks = %v", h.events)
	}
	if got := p.State().Executed; !reflect.DeepEqual(got, []string{here + "incFilter", here + "auditTap"}) {
		t.Fatalf("executed = %v", got)
	}
}

func TestValveIsIdentifiedByItsInnerFilter(t *testing.T) {
	p := NewPipeline().AddFilter(NewValve(incFilter{}, isOn{}))
	if _, err := p.Run(NewPayload(nil)); err != nil {
		t.Fatal(err)
	}
	if got := p.State().Skipped; !reflect.DeepEqual(got, []string{here + "incFilter"}) {
		t.Fatalf("skipped = %v", got)
	}
}

func TestNamedPipelineTypeNestsAsOneStep(t *testing.T) {
	outer := NewPipeline().AddFilter(incFilter{}).AddPipeline(newOnboarding())
	out, err := outer.Run(NewPayload(nil))
	if err != nil {
		t.Fatal(err)
	}
	if out.Get("n") != 2 {
		t.Fatalf("n = %v", out.Get("n"))
	}
	if got := outer.State().Executed; !reflect.DeepEqual(got, []string{here + "incFilter", here + "onboarding"}) {
		t.Fatalf("executed = %v", got)
	}
}

func TestAddSiteIsRecorded(t *testing.T) {
	p := NewPipeline().AddFilter(incFilter{})
	if site := p.StepSites()[here+"incFilter"]; !regexp.MustCompile(`step_identity_test\.go:\d+$`).MatchString(site) {
		t.Fatalf("site = %q", site)
	}
}

func refused(t *testing.T, want string, add func()) {
	t.Helper()
	defer func() {
		r := recover()
		err, ok := r.(*AnonymousStep)
		if !ok {
			t.Fatalf("expected *AnonymousStep panic, got %#v", r)
		}
		if !strings.Contains(err.Error(), want) {
			t.Fatalf("message %q lacks %q", err.Error(), want)
		}
	}()
	add()
}

type funcFilter func(Payload) (Payload, error)

func (f funcFilter) Call(p Payload) (Payload, error) { return f(p) }

func TestAnonymousStepsAreRefused(t *testing.T) {
	refused(t, "closure", func() {
		NewPipeline().AddFilter(funcFilter(func(p Payload) (Payload, error) { return p, nil })) // cup: allow-anonymous (a deliberate refusal test)
	})
	refused(t, "anonymous struct", func() {
		NewPipeline().AddTap(struct{ auditTap }{}) // cup: allow-anonymous (a deliberate refusal test)
	})
	refused(t, "closure", func() {
		NewValve(incFilter{}, predFunc(func(Payload) bool { return true })) // cup: allow-anonymous (a deliberate refusal test)
	})
	refused(t, "named pipeline type", func() {
		NewPipeline().AddPipeline(NewPipeline().AddFilter(incFilter{})) // cup: allow-anonymous (a deliberate refusal test)
	})
	refused(t, "package level", func() {
		NewValve(incFilter{}, predFunc(func(Payload) bool { return true })) // cup: allow-anonymous (a deliberate refusal test)
	})
}

func namedFunc(p Payload) (Payload, error) { return p, nil }

func TestAFuncAdapterIsIdentifiedByTheFunction(t *testing.T) {
	p := NewPipeline().AddFilter(funcFilter(namedFunc))
	if got := p.Identities(); !reflect.DeepEqual(got, []string{here + "namedFunc"}) {
		t.Fatalf("identities = %v", got)
	}
}

func TestPredicatesAreObjects(t *testing.T) {
	if got := NewValve(incFilter{}, isOn{}).PredicateSymbol; got != here+"isOn" {
		t.Fatalf("predicate symbol = %q", got)
	}
	p := NewPipeline().AddFilter(NewValve(incFilter{}, atLeast{5}))
	if out, _ := p.Run(NewPayload(map[string]any{"n": 5})); out.Get("n") != 6 {
		t.Fatalf("n = %v", out.Get("n"))
	}
	if out, _ := p.Run(NewPayload(map[string]any{"n": 1})); out.Get("n") != 1 {
		t.Fatalf("n = %v", out.Get("n"))
	}
}
