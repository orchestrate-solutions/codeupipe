// Pipeline: The Orchestrator
//
// Runs filters in sequence with hooks, taps, and state tracking.
// Supports batch (.Run) and streaming (.Stream) execution modes.
//
// Go-idiomatic: goroutines for parallel, channels for streaming.
//
// See also: TypeScript, Python, Rust, C# implementations.
package codeupipe

import (
	"fmt"
	"reflect"
	"strings"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// Step types
// ---------------------------------------------------------------------------

type stepKind int

const (
	filterStep stepKind = iota
	streamFilterStep
	tapStep
	parallelStep
	pipelineStep
)

type parallelGroup struct {
	filters []Filter
	names   []string
}

type step struct {
	name string // the step's identity (conformance/API.md, "Step identity")
	impl any    // Filter | StreamFilter | Tap | *parallelGroup | *Pipeline
	kind stepKind
}

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------

// Pipeline orchestrates filter execution with hooks, taps, and state tracking.
type Pipeline struct {
	steps          []step
	hooks          []Hook
	state          *State
	observeTiming  bool
	observeState   bool
	observeLineage bool
	disabledTaps   map[string]bool
	occurrences    map[string]int
	stepSites      map[string]string
}

// Nestable is a pipeline that can be nested as a step: a named type that
// embeds *Pipeline (type Onboarding struct{ *codeupipe.Pipeline }), the Go
// equivalent of a Pipeline subclass. *Pipeline satisfies it too, but a plain
// *Pipeline has no identity and AddPipeline refuses it.
type Nestable interface {
	AsPipeline() *Pipeline
}

// AsPipeline returns the pipeline itself (see Nestable).
func (p *Pipeline) AsPipeline() *Pipeline { return p }

// NewPipeline creates an empty Pipeline.
func NewPipeline() *Pipeline {
	return &Pipeline{
		state:        NewState(),
		observeState: true,
		disabledTaps: make(map[string]bool),
		occurrences:  make(map[string]int),
		stepSites:    make(map[string]string),
	}
}

// Identities returns each step's identity, in order.
func (p *Pipeline) Identities() []string {
	out := make([]string, len(p.steps))
	for i, s := range p.steps {
		out[i] = s.name
	}
	return out
}

// StepSites maps each identity to the file:line of the Add call (detail, not identity).
func (p *Pipeline) StepSites() map[string]string {
	out := make(map[string]string, len(p.stepSites))
	for k, v := range p.stepSites {
		out[k] = v
	}
	return out
}

// identity numbers a step's base identity from its second use.
func (p *Pipeline) identity(base string) string {
	p.occurrences[base]++
	id := base
	if n := p.occurrences[base]; n > 1 {
		id = fmt.Sprintf("%s#%d", base, n)
	}
	p.stepSites[id] = addSite()
	return id
}

// State returns the pipeline execution state after Run().
func (p *Pipeline) State() *State {
	return p.state
}

// -----------------------------------------------------------------------
// Builder API (fluent — returns *Pipeline for chaining)
// -----------------------------------------------------------------------

// AddFilter adds a filter (or Valve) to the pipeline, identified by its type.
func (p *Pipeline) AddFilter(f Filter) *Pipeline {
	p.steps = append(p.steps, step{name: p.identity(identify(f, "Filter")), impl: f, kind: filterStep})
	return p
}

// AddStreamFilter adds a stream filter to the pipeline.
func (p *Pipeline) AddStreamFilter(sf StreamFilter) *Pipeline {
	p.steps = append(p.steps, step{name: p.identity(identify(sf, "StreamFilter")), impl: sf, kind: streamFilterStep})
	return p
}

// AddTap adds an observation point to the pipeline.
func (p *Pipeline) AddTap(t Tap) *Pipeline {
	p.steps = append(p.steps, step{name: p.identity(identify(t, "Tap")), impl: t, kind: tapStep})
	return p
}

// UseHook attaches a lifecycle hook.
func (p *Pipeline) UseHook(h Hook) *Pipeline {
	p.hooks = append(p.hooks, h)
	return p
}

// AddParallel adds a parallel fan-out/fan-in group of filters, identified
// as parallel[<each filter's identity>].
func (p *Pipeline) AddParallel(filters []Filter) *Pipeline {
	fnames := make([]string, len(filters))
	for i, f := range filters {
		fnames[i] = identify(f, "Filter")
	}
	pg := &parallelGroup{filters: filters, names: fnames}
	id := p.identity("parallel[" + strings.Join(fnames, ",") + "]")
	p.steps = append(p.steps, step{name: id, impl: pg, kind: parallelStep})
	return p
}

// AddPipeline nests a named pipeline type as a single step inside this Pipeline.
func (p *Pipeline) AddPipeline(child Nestable) *Pipeline {
	if _, plain := child.(*Pipeline); plain {
		panic(&AnonymousStep{Message: "A nested pipeline must be a named pipeline type " +
			"(type Onboarding struct{ *codeupipe.Pipeline }), identified like a filter. " +
			"A plain *Pipeline can only run at the top level."})
	}
	id := p.identity(identify(child, "Nested pipeline"))
	p.steps = append(p.steps, step{name: id, impl: child.AsPipeline(), kind: pipelineStep})
	return p
}

// Observe enables observation features (timing, lineage tracking).
func (p *Pipeline) Observe(timing, lineage bool) *Pipeline {
	p.observeTiming = timing
	p.observeLineage = lineage
	return p
}

// ObserveState enables or disables state recording (executed/skipped/chunks/timings).
func (p *Pipeline) ObserveState(enabled bool) *Pipeline {
	p.observeState = enabled
	return p
}

func (p *Pipeline) markExecuted(name string) {
	if p.observeState {
		p.state.MarkExecuted(name)
	}
}

func (p *Pipeline) markSkipped(name string) {
	if p.observeState {
		p.state.MarkSkipped(name)
	}
}

func (p *Pipeline) incrementChunks(name string, count int) {
	if p.observeState {
		p.state.IncrementChunks(name, count)
	}
}

// DisableTaps (by identity) disables specific taps by name at runtime.
func (p *Pipeline) DisableTaps(names ...string) *Pipeline {
	for _, n := range names {
		p.disabledTaps[n] = true
	}
	return p
}

// EnableTaps re-enables previously disabled taps.
func (p *Pipeline) EnableTaps(names ...string) *Pipeline {
	for _, n := range names {
		delete(p.disabledTaps, n)
	}
	return p
}

// Call implements the Filter interface so pipelines can be nested.
func (p *Pipeline) Call(payload Payload) (Payload, error) {
	return p.Run(payload)
}

// -----------------------------------------------------------------------
// Batch execution
// -----------------------------------------------------------------------

// canRunFast reports whether the hot path can bypass hooks, timing,
// lineage, and taps entirely.
func (p *Pipeline) canRunFast() bool {
	if len(p.hooks) > 0 || p.observeTiming || p.observeLineage || len(p.disabledTaps) > 0 {
		return false
	}
	for _, s := range p.steps {
		if s.kind != filterStep && s.kind != parallelStep {
			return false
		}
	}
	return true
}

// runFast is the hot path — filter/parallel only, no hooks, no timing,
// no lineage, no taps. Skips per-step time.Now() and hook iteration.
func (p *Pipeline) runFast(initialPayload Payload) (Payload, error) {
	if p.observeState {
		p.state = NewState()
		p.state.Executed = make([]string, 0, len(p.steps))
		p.state.Skipped = make([]string, 0, len(p.steps))
		p.state.Errors = make([]StateError, 0, len(p.steps))
		p.state.ChunksProcessed = make(map[string]int, len(p.steps))
		p.state.Timings = make(map[string]float64, len(p.steps))
	} else {
		p.state = &State{}
	}
	payload := initialPayload
	observe := p.observeState

	for _, s := range p.steps {
		switch s.kind {
		case parallelStep:
			pg := s.impl.(*parallelGroup)
			results, err := p.runParallel(pg.filters, payload)
			if err != nil {
				return Payload{}, err
			}
			for _, r := range results {
				payload = payload.Merge(r)
			}
			if observe {
				p.state.MarkExecuted(s.name)
			}
		default: // filterStep — canRunFast guarantees this
			f := s.impl.(Filter)
			result, err := f.Call(payload)
			if err != nil {
				return Payload{}, err
			}
			payload = result
			if observe {
				if valve, ok := f.(*Valve); ok && valve.LastSkipped {
					p.state.MarkSkipped(s.name)
				} else {
					p.state.MarkExecuted(s.name)
				}
			}
		}
	}
	return payload, nil
}

// Run executes the pipeline in batch mode.
func (p *Pipeline) Run(initialPayload Payload) (Payload, error) {
	// Reject StreamFilters in batch mode
	for _, s := range p.steps {
		if s.kind == streamFilterStep {
			return Payload{}, fmt.Errorf(
				"pipeline contains StreamFilter '%s'; use pipeline.Stream() instead",
				s.name,
			)
		}
	}

	if p.canRunFast() {
		return p.runFast(initialPayload)
	}

	if p.observeState {
		p.state = NewState()
		p.state.Executed = make([]string, 0, len(p.steps))
		p.state.Skipped = make([]string, 0, len(p.steps))
		p.state.Errors = make([]StateError, 0, len(p.steps))
		p.state.ChunksProcessed = make(map[string]int, len(p.steps))
		p.state.Timings = make(map[string]float64, len(p.steps))
	} else {
		p.state = &State{}
	}
	payload := initialPayload

	// Hook: pipeline start
	for _, h := range p.hooks {
		h.Before("", payload)
	}

	var stepName string

	for _, s := range p.steps {
		stepName = s.name

		// --- Tap ---
		if s.kind == tapStep {
			if p.disabledTaps[s.name] {
				p.markSkipped(s.name)
				continue
			}
			p.observe(s.name, s.impl.(Tap), payload)
			p.markExecuted(s.name)
			continue
		}

		t0 := time.Now()

		switch s.kind {
		case parallelStep:
			// Goroutine-based parallel execution
			pg := s.impl.(*parallelGroup)
			results, err := p.runParallel(pg.filters, payload)
			if err != nil {
				p.recordTimingIfEnabled(s.name, t0)
				p.fireError(s.name, err, payload)
				return Payload{}, err
			}
			for _, r := range results {
				payload = payload.Merge(r)
			}
			p.markExecuted(s.name)

		case pipelineStep:
			child := s.impl.(*Pipeline)
			for _, h := range p.hooks {
				h.Before(s.name, payload)
			}
			result, err := child.Run(payload)
			if err != nil {
				p.recordTimingIfEnabled(s.name, t0)
				p.fireError(s.name, err, payload)
				return Payload{}, err
			}
			payload = result
			p.markExecuted(s.name)
			for _, h := range p.hooks {
				h.After(s.name, payload)
			}

		default: // filterStep
			f := s.impl.(Filter)
			for _, h := range p.hooks {
				h.Before(s.name, payload)
			}

			result, err := f.Call(payload)
			if err != nil {
				p.recordTimingIfEnabled(s.name, t0)
				p.fireError(s.name, err, payload)
				return Payload{}, err
			}
			payload = result

			// Valve skip detection
			if valve, ok := f.(*Valve); ok && valve.LastSkipped {
				p.markSkipped(s.name)
			} else {
				p.markExecuted(s.name)
			}

			for _, h := range p.hooks {
				h.After(s.name, payload)
			}
		}

		p.recordTimingIfEnabled(s.name, t0)
		if p.observeLineage {
			payload = payload.Stamp(s.name)
		}
	}

	// Hook: pipeline end
	for _, h := range p.hooks {
		h.After("", payload)
	}

	_ = stepName // suppress unused warning
	return payload, nil
}

// -----------------------------------------------------------------------
// Streaming
// -----------------------------------------------------------------------

// Stream processes payloads from source through the pipeline, writing
// results to out. Both channels carry Payload values.
//
// The caller closes source when done sending. Stream closes out when
// all processing finishes. Returns any error encountered.
func (p *Pipeline) Stream(source <-chan Payload) (<-chan Payload, <-chan error) {
	out := make(chan Payload)
	errCh := make(chan error, 1)

	go func() {
		defer close(out)

		if p.observeState {
			p.state = NewState()
			p.state.Executed = make([]string, 0, len(p.steps))
			p.state.Skipped = make([]string, 0, len(p.steps))
			p.state.Errors = make([]StateError, 0, len(p.steps))
			p.state.ChunksProcessed = make(map[string]int, len(p.steps))
			p.state.Timings = make(map[string]float64, len(p.steps))
		} else {
			p.state = &State{}
		}

		sentinel := NewPayload(nil)
		for _, h := range p.hooks {
			h.Before("", sentinel)
		}

		var err error
		current := source

		for _, s := range p.steps {
			current = p.wrapStep(current, s)
		}

		for payload := range current {
			out <- payload
		}

		// Check for sentinel error from step wrappers
		if err != nil {
			for _, h := range p.hooks {
				h.OnError("", err, sentinel)
			}
			errCh <- err
			return
		}

		for _, h := range p.hooks {
			h.After("", sentinel)
		}
	}()

	return out, errCh
}

func (p *Pipeline) wrapStep(upstream <-chan Payload, s step) <-chan Payload {
	out := make(chan Payload)

	go func() {
		defer close(out)

		switch s.kind {
		case tapStep:
			if p.disabledTaps[s.name] {
				p.markSkipped(s.name)
				for payload := range upstream {
					out <- payload
				}
				return
			}
			p.markExecutedOnce(s.name)
			tap := s.impl.(Tap)
			for payload := range upstream {
				p.observe(s.name, tap, payload)
				p.incrementChunks(s.name, 1)
				out <- payload
			}

		case streamFilterStep:
			p.markExecutedOnce(s.name)
			sf := s.impl.(StreamFilter)
			for chunk := range upstream {
				results, err := sf.Stream(chunk)
				if err != nil {
					// Propagate error by stopping
					return
				}
				for _, r := range results {
					p.incrementChunks(s.name, 1)
					out <- r
				}
			}

		case filterStep:
			p.markExecutedOnce(s.name)
			f := s.impl.(Filter)
			for chunk := range upstream {
				result, err := f.Call(chunk)
				if err != nil {
					return
				}
				p.incrementChunks(s.name, 1)
				out <- result
			}

		case parallelStep:
			p.markExecutedOnce(s.name)
			pg := s.impl.(*parallelGroup)
			for chunk := range upstream {
				results, err := p.runParallel(pg.filters, chunk)
				if err != nil {
					return
				}
				merged := chunk
				for _, r := range results {
					merged = merged.Merge(r)
				}
				p.incrementChunks(s.name, 1)
				out <- merged
			}

		case pipelineStep:
			p.markExecutedOnce(s.name)
			child := s.impl.(*Pipeline)
			for chunk := range upstream {
				result, err := child.Run(chunk)
				if err != nil {
					return
				}
				p.incrementChunks(s.name, 1)
				out <- result
			}
		}
	}()

	return out
}

// -----------------------------------------------------------------------
// Introspection
// -----------------------------------------------------------------------

// StepInfo describes a single step for introspection.
type StepInfo struct {
	Name     string     `json:"name"`
	Type     string     `json:"type"`
	Class    string     `json:"class,omitempty"`
	Filters  []StepInfo `json:"filters,omitempty"`
	Children []StepInfo `json:"children,omitempty"`
}

// DescribeResult is the output of Describe().
type DescribeResult struct {
	Steps     []StepInfo `json:"steps"`
	Hooks     []string   `json:"hooks"`
	StepCount int        `json:"step_count"`
}

// Describe returns a machine-readable tree of the pipeline structure.
func (p *Pipeline) Describe() DescribeResult {
	steps := make([]StepInfo, 0, len(p.steps))

	for _, s := range p.steps {
		switch s.kind {
		case parallelStep:
			pg := s.impl.(*parallelGroup)
			children := make([]StepInfo, len(pg.filters))
			for i, f := range pg.filters {
				children[i] = StepInfo{
					Name: pg.names[i],
					Type: "filter",
				}
				_ = f
			}
			steps = append(steps, StepInfo{
				Name:    s.name,
				Type:    "parallel",
				Filters: children,
			})

		case pipelineStep:
			child := s.impl.(*Pipeline)
			desc := child.Describe()
			steps = append(steps, StepInfo{
				Name:     s.name,
				Type:     "pipeline",
				Children: desc.Steps,
			})

		default:
			steps = append(steps, StepInfo{
				Name:  s.name,
				Type:  kindString(s.kind),
				Class: typeName(s.impl),
			})
		}
	}

	hookNames := make([]string, len(p.hooks))
	for i, h := range p.hooks {
		hookNames[i] = typeName(h)
	}

	return DescribeResult{
		Steps:     steps,
		Hooks:     hookNames,
		StepCount: len(steps),
	}
}

// -----------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------

func (p *Pipeline) runParallel(filters []Filter, payload Payload) ([]Payload, error) {
	results := make([]Payload, len(filters))
	errs := make([]error, len(filters))
	var wg sync.WaitGroup

	for i, f := range filters {
		wg.Add(1)
		go func(idx int, filter Filter) {
			defer wg.Done()
			r, err := filter.Call(payload)
			results[idx] = r
			errs[idx] = err
		}(i, f)
	}
	wg.Wait()

	for _, err := range errs {
		if err != nil {
			return nil, err
		}
	}
	return results, nil
}

func (p *Pipeline) recordTimingIfEnabled(name string, t0 time.Time) {
	if p.observeState && p.observeTiming {
		p.state.RecordTiming(name, time.Since(t0).Seconds())
	}
}

// observe runs a Tap on Plane B: a Tap failure never halts the pipeline.
// Go Taps fail by panicking (Observe returns nothing), so the panic is
// recovered and recorded in State.Errors under the Tap's name, and the run
// continues. Same contract as Python codeupipe.core; the shared
// cases are conformance/cases/tap.json.
func (p *Pipeline) observe(name string, tap Tap, payload Payload) {
	defer func() {
		if r := recover(); r != nil && p.observeState {
			p.state.RecordError(name, fmt.Errorf("tap %s panicked: %v", name, r))
		}
	}()
	tap.Observe(payload)
}

// fireError notifies hooks of a failed step: OnError for the failing step,
// then for the pipeline (filterName ""), mirroring Before/After, which fire
// at both levels. Same contract in every runtime (conformance/cases/hook.json).
func (p *Pipeline) fireError(step string, err error, payload Payload) {
	for _, h := range p.hooks {
		h.OnError(step, err, payload)
	}
	for _, h := range p.hooks {
		h.OnError("", err, payload)
	}
}

func (p *Pipeline) markExecutedOnce(name string) {
	for _, n := range p.state.Executed {
		if n == name {
			return
		}
	}
	p.state.MarkExecuted(name)
}

func typeName(v any) string {
	t := reflect.TypeOf(v)
	if t.Kind() == reflect.Ptr {
		t = t.Elem()
	}
	return t.Name()
}

func kindString(k stepKind) string {
	switch k {
	case filterStep:
		return "filter"
	case streamFilterStep:
		return "stream_filter"
	case tapStep:
		return "tap"
	case parallelStep:
		return "parallel"
	case pipelineStep:
		return "pipeline"
	default:
		return "unknown"
	}
}
