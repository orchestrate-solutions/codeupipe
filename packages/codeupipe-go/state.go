package codeupipe

import (
	"maps"
	"time"
)

// State records what happened in one run: the steps that executed, the
// steps that a Valve skipped, the errors, and the time of each step when
// timing is on.
//
// A State belongs to one run. Give one to Pipeline.RunWithState, or read the
// State of the run that started last with Pipeline.State. A failed run keeps
// the steps that completed before the failure.
type State struct {
	executed []string
	skipped  []string
	errors   []StepFailure
	timings  map[string]time.Duration
}

// NewState gives an empty State, for a caller that gives the State of a run.
func NewState() *State {
	return &State{}
}

// Executed gives the labels of the steps that ran, in order.
func (s *State) Executed() []string {
	return append([]string{}, s.executed...)
}

// Skipped gives the labels of the steps that a Valve did not run.
func (s *State) Skipped() []string {
	return append([]string{}, s.skipped...)
}

// Errors gives the errors of the run, each with the label of its step.
func (s *State) Errors() []StepFailure {
	return append([]StepFailure{}, s.errors...)
}

// Timings gives the time of each step, by label, when timing is on.
func (s *State) Timings() map[string]time.Duration {
	if s.timings == nil {
		return map[string]time.Duration{}
	}
	return maps.Clone(s.timings)
}

func (s *State) markExecuted(label string) {
	s.executed = append(s.executed, label)
}

func (s *State) markSkipped(label string) {
	s.skipped = append(s.skipped, label)
}

func (s *State) recordError(label string, err error) {
	s.errors = append(s.errors, StepFailure{Label: label, Err: err})
}

func (s *State) recordTiming(label string, elapsed time.Duration) {
	if s.timings == nil {
		s.timings = make(map[string]time.Duration)
	}
	s.timings[label] = elapsed
}
