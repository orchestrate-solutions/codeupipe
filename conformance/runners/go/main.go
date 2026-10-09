// Go conformance runner: executes cases, reports what happened.
//
//	go run . < cases.json > results.json
//
// Mirrors conformance/runners/python/runner.py; conformance/run.py judges.
// Go's Tap.Observe returns nothing, so the reference "fail" Tap panics, which
// is how a Go Tap signals failure.
package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	cup "github.com/codeuchain/codeupipe-core/codeupipe"
)

type stepSpec struct {
	Kind    string         `json:"kind"`
	Name    string         `json:"name"`
	Op      string         `json:"op"`
	Key     string         `json:"key"`
	Value   any            `json:"value"`
	From    string         `json:"from"`
	To      string         `json:"to"`
	By      float64        `json:"by"`
	Message string         `json:"message"`
	When    map[string]any `json:"when"`
	Filter  *stepSpec      `json:"filter"`
	Steps   []stepSpec     `json:"steps"`
}

type caseSpec struct {
	ID    string         `json:"id"`
	Steps []stepSpec     `json:"steps"`
	Input map[string]any `json:"input"`
	Hooks any            `json:"hooks"` // true (record) or "noop" (benchmarks)
}

var taps []any
var hooks []string

// --- reference steps -------------------------------------------------------

type opFilter struct{ spec stepSpec }

func (f opFilter) Call(p cup.Payload) (cup.Payload, error) {
	s := f.spec
	switch s.Op {
	case "set":
		return p.Insert(s.Key, s.Value), nil
	case "copy":
		return p.Insert(s.To, p.Get(s.From)), nil
	case "add":
		current, _ := p.Get(s.Key, 0.0).(float64)
		return p.Insert(s.Key, current+s.By), nil
	case "append":
		existing, _ := p.Get(s.Key).([]any)
		next := append(append([]any{}, existing...), s.Value)
		return p.Insert(s.Key, next), nil
	case "remove":
		return p.Remove(s.Key), nil
	case "merge":
		other, _ := s.Value.(map[string]any)
		return p.Merge(cup.NewPayload(other)), nil
	case "has":
		return p.Insert(s.To, p.Has(s.Key)), nil
	case "mutate":
		m := p.WithMutation()
		m.Set(s.Key, s.Value)
		return m.ToImmutable(), nil
	case "fail":
		return p, errors.New(s.Message)
	}
	return p, fmt.Errorf("unknown filter op %q", s.Op)
}

type opTap struct{ spec stepSpec }

func (t opTap) Observe(p cup.Payload) {
	switch t.spec.Op {
	case "fail":
		panic(t.spec.Message)
	case "noop":
		return
	}
	taps = append(taps, p.Get(t.spec.Key))
}

type noopHook struct{ cup.DefaultHook }

type recordHook struct{}

func (recordHook) Before(name string, _ cup.Payload)           { hooks = append(hooks, "before:"+name) }
func (recordHook) After(name string, _ cup.Payload)            { hooks = append(hooks, "after:"+name) }
func (recordHook) OnError(name string, _ error, _ cup.Payload) { hooks = append(hooks, "error:"+name) }

// Valve predicates are objects (conformance/API.md, "Valve"): named types
// with Test, the case's condition in their fields.
type equalsWhen struct {
	key   string
	value any
}

func (w equalsWhen) Test(p cup.Payload) bool { return jsonEqual(p.Get(w.key), w.value) }

type truthyWhen struct{ key string }

func (w truthyWhen) Test(p cup.Payload) bool { return truthy(p.Get(w.key)) }

func predicate(when map[string]any) (cup.Predicate, error) {
	key, _ := when["key"].(string)
	switch when["op"] {
	case "equals":
		return equalsWhen{key, when["value"]}, nil
	case "truthy":
		return truthyWhen{key}, nil
	}
	return nil, fmt.Errorf("unknown valve op %v", when["op"])
}

// nested is the runner's named pipeline type: only named pipeline types can
// be nested (step identity).
type nested struct{ *cup.Pipeline }

func truthy(v any) bool {
	switch x := v.(type) {
	case nil:
		return false
	case bool:
		return x
	case float64:
		return x != 0
	case string:
		return x != ""
	case []any:
		return len(x) > 0
	case map[string]any:
		return len(x) > 0
	}
	return true
}

func jsonEqual(a, b any) bool {
	ja, _ := json.Marshal(a)
	jb, _ := json.Marshal(b)
	return string(ja) == string(jb)
}

// --- building + running ----------------------------------------------------

func build(steps []stepSpec) (*cup.Pipeline, error) {
	p := cup.NewPipeline()
	for _, s := range steps {
		switch s.Kind {
		case "filter":
			p.AddFilter(opFilter{s})
		case "tap":
			p.AddTap(opTap{s})
		case "valve":
			pred, err := predicate(s.When)
			if err != nil {
				return nil, err
			}
			p.AddFilter(cup.NewValve(opFilter{*s.Filter}, pred))
		case "pipeline":
			child, err := build(s.Steps)
			if err != nil {
				return nil, err
			}
			p.AddPipeline(nested{child})
		default:
			return nil, fmt.Errorf("unknown step kind %q", s.Kind)
		}
	}
	return p, nil
}

func runCase(c caseSpec) (result map[string]any) {
	taps, hooks = []any{}, []string{}
	result = map[string]any{"id": c.ID}
	p, err := build(c.Steps)
	if err != nil {
		return map[string]any{"id": c.ID, "unsupported": err.Error()}
	}
	withHooks := c.Hooks == true
	if withHooks {
		p.UseHook(recordHook{})
	}
	input := c.Input
	if input == nil {
		input = map[string]any{}
	}
	func() {
		defer func() {
			if r := recover(); r != nil {
				result["error"] = fmt.Sprintf("panic: %v", r)
			}
		}()
		out, runErr := p.Run(cup.NewPayload(input))
		if runErr != nil {
			result["error"] = runErr.Error()
		} else {
			result["output"] = out.ToDict()
		}
	}()
	// Steps are identified by their filter (conformance/API.md); the cases
	// name them. Each case step adds one pipeline step, in order, so map the
	// identities back; an identity this map does not know stays and fails.
	label := map[string]string{}
	for i, id := range p.Identities() {
		label[id] = c.Steps[i].Name
	}
	named := func(ids []string) []string {
		out := []string{}
		for _, id := range ids {
			if n, ok := label[id]; ok {
				id = n
			}
			out = append(out, id)
		}
		return out
	}
	state := p.State()
	errorIDs := []string{}
	for _, e := range state.Errors {
		errorIDs = append(errorIDs, e.Name)
	}
	result["state"] = map[string]any{
		"executed": named(state.Executed),
		"skipped":  named(state.Skipped),
		"errors":   named(errorIDs),
	}
	if withHooks {
		mapped := []string{}
		for _, h := range hooks {
			phase, id, _ := strings.Cut(h, ":")
			if n, ok := label[id]; ok {
				id = n
			}
			mapped = append(mapped, phase+":"+id)
		}
		result["hooks"] = mapped
	}
	result["taps"] = taps
	result["input_after"] = input
	return result
}

func nonNil(xs []string) []string {
	if xs == nil {
		return []string{}
	}
	return xs
}

const (
	benchWarmup  = 20000
	benchRuns    = 20000
	benchRepeats = 5
)

// bench times each scenario: best of benchRepeats x benchRuns, in µs/run.
func bench(cases []caseSpec) []map[string]any {
	out := make([]map[string]any, 0, len(cases))
	for _, c := range cases {
		p, err := build(c.Steps)
		if err != nil {
			out = append(out, map[string]any{"id": c.ID, "unsupported": err.Error()})
			continue
		}
		if c.Hooks == "noop" {
			p.UseHook(noopHook{})
		}
		run := func() cup.Payload {
			r, err := p.Run(cup.NewPayload(c.Input))
			if err != nil {
				panic(err)
			}
			return r
		}
		output := run().ToDict()
		for i := 0; i < benchWarmup; i++ {
			run()
		}
		best := time.Duration(1<<63 - 1)
		for r := 0; r < benchRepeats; r++ {
			t0 := time.Now()
			for i := 0; i < benchRuns; i++ {
				run()
			}
			if d := time.Since(t0); d < best {
				best = d
			}
		}
		us := float64(best.Nanoseconds()) / benchRuns / 1000
		out = append(out, map[string]any{"id": c.ID, "us_per_run": us, "output": output})
	}
	return out
}

func main() {
	var cases []caseSpec
	if err := json.NewDecoder(os.Stdin).Decode(&cases); err != nil {
		fmt.Fprintln(os.Stderr, "bad cases:", err)
		os.Exit(2)
	}
	var results []map[string]any
	if len(os.Args) > 1 && os.Args[1] == "bench" {
		results = bench(cases)
	} else {
		results = make([]map[string]any, 0, len(cases))
		for _, c := range cases {
			results = append(results, runCase(c))
		}
	}
	if err := json.NewEncoder(os.Stdout).Encode(results); err != nil {
		fmt.Fprintln(os.Stderr, "encode:", err)
		os.Exit(2)
	}
}
