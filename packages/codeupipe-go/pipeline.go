package codeupipe

import (
	"context"
	"strconv"
	"sync"
	"time"
)

// PipelineOf runs steps in order on data of type P. Pipeline is the form for
// a Payload; see PipelineData for a type of your own.
//
// Filters change the data, Valves gate a Filter, Taps read, Hooks see the
// lifecycle, and State records what ran. Add steps with AddFilter,
// AddValve, AddTap and AddPipeline, add Hooks with UseHook, and run with
// Run.
//
// A Pipeline can be run from many goroutines at the same time: each run
// writes into a State of its own. Add the steps before the first run. Adding
// a step while a run is in progress is not supported.
type PipelineOf[P PipelineData[P]] struct {
	label   string
	steps   []step[P]
	uses    map[string]int
	hooks   []HookOf[P]
	timing  bool
	lineage bool

	runs sync.Mutex // guards started and last
	// The number of runs that have started; the number of a run is its ticket.
	started uint64
	// The State of the run that started last, once it has ended.
	last *State
}

// Pipeline runs steps in order on a Payload.
type Pipeline = PipelineOf[*Payload]

// step is one step of a pipeline, with its label: a Filter, a Valve, a Tap
// or a nested pipeline. One of the four is set.
type step[P PipelineData[P]] struct {
	label    string
	filter   FilterOf[P]
	valve    *valve[P]
	tap      TapOf[P]
	pipeline *PipelineOf[P]
}

// NewPipeline gives a pipeline with no steps. Nested, its label is
// "Pipeline". A pipeline type of your own is a NamedPipeline.
func NewPipeline() *Pipeline {
	return NewPipelineOf[*Payload]()
}

// NewPipelineOf is NewPipeline for a pipeline that carries P.
func NewPipelineOf[P PipelineData[P]]() *PipelineOf[P] {
	return &PipelineOf[P]{label: "Pipeline"}
}

// State gives the State of the run that started last, once it has ended.
//
// A State belongs to one run, and this is for a caller with one run at a
// time. A caller with more than one run at a time gives each run its own
// State (RunWithState). Before the first run has ended, the State is empty.
func (p *PipelineOf[P]) State() *State {
	p.runs.Lock()
	defer p.runs.Unlock()
	if p.last == nil {
		return NewState()
	}
	return p.last
}

// Labels gives the label of each step, in order.
func (p *PipelineOf[P]) Labels() []string {
	labels := make([]string, len(p.steps))
	for i := range p.steps {
		labels[i] = p.steps[i].label
	}
	return labels
}

// AddFilter adds a Filter.
func (p *PipelineOf[P]) AddFilter(filter FilterOf[P]) {
	if filter == nil {
		panic("codeupipe: AddFilter needs a Filter, a value with Call(ctx, payload). It was given nil")
	}
	p.push(labelOf(filter), step[P]{filter: filter})
}

// AddValve adds a Valve: filter runs only when predicate.Test is true.
//
// The condition comes first, then the Filter that it controls. When the
// test is false the data passes through unchanged and the step is recorded
// as skipped. The step has the label of its Filter.
func (p *PipelineOf[P]) AddValve(predicate PredicateOf[P], filter FilterOf[P]) {
	if predicate == nil {
		panic("codeupipe: AddValve needs a Predicate, a value with Test(ctx, payload). It was given nil")
	}
	if filter == nil {
		panic("codeupipe: AddValve needs a Filter, a value with Call(ctx, payload). It was given nil")
	}
	p.push(labelOf(filter), step[P]{valve: &valve[P]{predicate: predicate, filter: filter}})
}

// AddTap adds a Tap.
func (p *PipelineOf[P]) AddTap(tap TapOf[P]) {
	if tap == nil {
		panic("codeupipe: AddTap needs a Tap, a value with Observe(ctx, payload). It was given nil")
	}
	p.push(labelOf(tap), step[P]{tap: tap})
}

// AddPipeline nests a Pipeline as one step of this Pipeline. Its label is
// the name of its NamedPipeline type, or "Pipeline".
func (p *PipelineOf[P]) AddPipeline(pipeline *PipelineOf[P]) {
	if pipeline == nil {
		panic("codeupipe: AddPipeline needs a Pipeline. It was given nil")
	}
	p.push(pipeline.label, step[P]{pipeline: pipeline})
}

// UseHook adds a Hook.
func (p *PipelineOf[P]) UseHook(hook HookOf[P]) {
	if hook == nil {
		panic("codeupipe: UseHook needs a Hook, a value with Before, After and OnError. It was given nil")
	}
	p.hooks = append(p.hooks, hook)
}

// Observe turns timing (the time of each step, in State) and lineage (labels
// on the data) on or off. Both are off by default. A type of your own keeps
// lineage only if it has Stamp(label string).
func (p *PipelineOf[P]) Observe(timing, lineage bool) {
	p.timing = timing
	p.lineage = lineage
}

// push adds a step, with the label base, numbered from its second use in
// this pipeline: "AddFilter", "AddFilter#2".
func (p *PipelineOf[P]) push(base string, s step[P]) {
	if p.uses == nil {
		p.uses = make(map[string]int)
	}
	p.uses[base]++
	s.label = base
	if count := p.uses[base]; count > 1 {
		s.label = base + "#" + strconv.Itoa(count)
	}
	p.steps = append(p.steps, s)
}

// Run runs the steps in order on a copy of input, and returns the result.
// The caller's data is not changed.
//
// A Filter failure stops the run. The Hooks see it, and Run returns that
// same error. A Tap failure is recorded in State and the run goes on. The
// run writes into a new State, which State gives once the run has ended.
//
// The Pipeline gives ctx to each step and does nothing else with it: a
// cancelled ctx does not stop the run between steps.
func (p *PipelineOf[P]) Run(ctx context.Context, input P) (P, error) {
	return p.RunWithState(ctx, input, NewState())
}

// RunWithState is Run, writing into state, which the caller gives. A caller
// with more than one run at a time gives each run its own State.
func (p *PipelineOf[P]) RunWithState(ctx context.Context, input P, state *State) (P, error) {
	if state == nil {
		panic("codeupipe: RunWithState needs a State. NewState makes one")
	}
	if state.executed == nil {
		// Room for every step, so that the list grows once and not at each step.
		state.executed = make([]string, 0, len(p.steps))
	}
	ticket := p.start()
	payload, err := p.runSteps(ctx, input.Copy(), state)
	p.end(ticket, state)
	if err != nil {
		var none P
		return none, err
	}
	return payload, nil
}

// start gives a run its ticket.
func (p *PipelineOf[P]) start() uint64 {
	p.runs.Lock()
	defer p.runs.Unlock()
	p.started++
	return p.started
}

// end keeps state as the State of the pipeline, unless a run that started
// later has ended already (a run inside this run, or in another goroutine).
func (p *PipelineOf[P]) end(ticket uint64, state *State) {
	p.runs.Lock()
	defer p.runs.Unlock()
	if ticket == p.started {
		p.last = state
	}
}

func (p *PipelineOf[P]) runSteps(ctx context.Context, payload P, state *State) (P, error) {
	for _, hook := range p.hooks {
		hook.Before(ctx, "", payload)
	}

	for i := range p.steps {
		s := &p.steps[i]
		if s.tap != nil {
			if err := s.tap.Observe(ctx, payload); err != nil {
				state.recordError(s.label, err)
			}
			state.markExecuted(s.label)
			continue
		}

		var started time.Time
		if p.timing {
			started = time.Now()
		}
		for _, hook := range p.hooks {
			hook.Before(ctx, s.label, payload)
		}

		ran, err := s.run(ctx, &payload)
		if err != nil {
			if p.timing {
				state.recordTiming(s.label, time.Since(started))
			}
			// The failing step first, then the pipeline: OnError fires at
			// both levels, as Before and After do.
			for _, hook := range p.hooks {
				hook.OnError(ctx, s.label, err, payload)
			}
			for _, hook := range p.hooks {
				hook.OnError(ctx, "", err, payload)
			}
			return payload, err
		}
		if ran {
			state.markExecuted(s.label)
		} else {
			state.markSkipped(s.label)
		}

		for _, hook := range p.hooks {
			hook.After(ctx, s.label, payload)
		}
		if p.timing {
			state.recordTiming(s.label, time.Since(started))
		}
		if p.lineage {
			if stamps, ok := any(payload).(stamper); ok {
				stamps.Stamp(s.label)
			}
		}
	}

	for _, hook := range p.hooks {
		hook.After(ctx, "", payload)
	}
	return payload, nil
}

// run runs a step that Hooks see. It is false for a Valve that skipped its
// Filter.
func (s *step[P]) run(ctx context.Context, payload *P) (bool, error) {
	switch {
	case s.filter != nil:
		return true, s.filter.Call(ctx, *payload)
	case s.valve != nil:
		if !s.valve.predicate.Test(ctx, *payload) {
			return false, nil
		}
		return true, s.valve.filter.Call(ctx, *payload)
	default:
		// A run of its own, with its own State: a failure inside leaves this
		// data as it was.
		out, err := s.pipeline.Run(ctx, *payload)
		if err != nil {
			return true, err
		}
		*payload = out
		return true, nil
	}
}
