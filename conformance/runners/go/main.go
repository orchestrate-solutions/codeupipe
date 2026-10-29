// The Go conformance runner: it runs the cases and reports what happened.
//
//	go run . <target> < cases.json > results.json
//
// Targets:
//
//	run         the Pipeline of packages/codeupipe-go
//	bench:run   the same, timed on the scenarios of conformance/bench
//
// The runner never judges; conformance/run.py compares the results of every
// target with the same expectations.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/conformance/runners/go/cup_ops"
	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// unsupported is a case that this runner cannot express. It is reported,
// never judged.
type unsupported string

func (u unsupported) Error() string { return string(u) }

func field(spec map[string]any, name string) (any, error) {
	value, ok := spec[name]
	if !ok {
		return nil, unsupported(fmt.Sprintf("the step has no '%s'", name))
	}
	return value, nil
}

func text(spec map[string]any, name string) (string, error) {
	value, err := field(spec, name)
	if err != nil {
		return "", err
	}
	s, ok := value.(string)
	if !ok {
		return "", unsupported(fmt.Sprintf("'%s' is not a string", name))
	}
	return s, nil
}

func number(spec map[string]any, name string) (float64, error) {
	value, err := field(spec, name)
	if err != nil {
		return 0, err
	}
	n, ok := value.(float64)
	if !ok {
		return 0, unsupported(fmt.Sprintf("'%s' is not a number", name))
	}
	return n, nil
}

func object(spec map[string]any, name string) (map[string]any, error) {
	value, err := field(spec, name)
	if err != nil {
		return nil, err
	}
	m, ok := value.(map[string]any)
	if !ok {
		return nil, unsupported(fmt.Sprintf("'%s' is not an object", name))
	}
	return m, nil
}

// filterOf gives the Filter of a step of the case.
func filterOf(spec map[string]any) (codeupipe.Filter, error) {
	op, err := text(spec, "op")
	if err != nil {
		return nil, err
	}
	var key, other string
	var problem error
	read := func(name string) string {
		s, err := text(spec, name)
		if err != nil && problem == nil {
			problem = err
		}
		return s
	}
	switch op {
	case "set", "mutate", "append":
		key = read("key")
		value, err := field(spec, "value")
		if err != nil {
			return nil, err
		}
		if problem != nil {
			return nil, problem
		}
		switch op {
		case "set":
			return cup_ops.SetFilter{Key: key, Value: value}, nil
		case "mutate":
			return cup_ops.MutateFilter{Key: key, Value: value}, nil
		}
		return cup_ops.AppendFilter{Key: key, Value: value}, nil
	case "copy":
		key, other = read("from"), read("to")
		return cup_ops.CopyFilter{From: key, To: other}, problem
	case "add":
		key = read("key")
		by, err := number(spec, "by")
		if err != nil {
			return nil, err
		}
		return cup_ops.AddFilter{Key: key, By: by}, problem
	case "remove":
		key = read("key")
		return cup_ops.RemoveFilter{Key: key}, problem
	case "merge":
		value, err := object(spec, "value")
		if err != nil {
			return nil, err
		}
		return cup_ops.MergeFilter{Value: value}, nil
	case "has":
		key, other = read("key"), read("to")
		return cup_ops.HasFilter{Key: key, To: other}, problem
	case "fail":
		return cup_ops.FailFilter{Message: read("message")}, problem
	case "run_again":
		input, err := object(spec, "input")
		if err != nil {
			return nil, err
		}
		return cup_ops.RunAgainFilter{Input: input}, nil
	}
	return nil, unsupported(fmt.Sprintf("unknown filter op '%s'", op))
}

// tapOf gives the Tap of a step of the case.
func tapOf(spec map[string]any) (codeupipe.Tap, error) {
	op, err := text(spec, "op")
	if err != nil {
		return nil, err
	}
	switch op {
	case "record":
		key, err := text(spec, "key")
		return cup_ops.RecordTap{Key: key}, err
	case "fail":
		message, err := text(spec, "message")
		return cup_ops.FailTap{Message: message}, err
	case "noop":
		return cup_ops.NoopTap{}, nil
	}
	return nil, unsupported(fmt.Sprintf("unknown tap op '%s'", op))
}

// predicateOf gives the Predicate of the "when" of a valve.
func predicateOf(when map[string]any) (codeupipe.Predicate, error) {
	op, err := text(when, "op")
	if err != nil {
		return nil, err
	}
	key, err := text(when, "key")
	if err != nil {
		return nil, err
	}
	switch op {
	case "equals":
		value, err := field(when, "value")
		return cup_ops.EqualsPredicate{Key: key, Value: value}, err
	case "truthy":
		return cup_ops.TruthyPredicate{Key: key}, nil
	}
	return nil, unsupported(fmt.Sprintf("unknown valve op '%s'", op))
}

func stepsOf(spec map[string]any) ([]any, error) {
	value, err := field(spec, "steps")
	if err != nil {
		return nil, err
	}
	steps, ok := value.([]any)
	if !ok {
		return nil, unsupported("'steps' is not a list")
	}
	return steps, nil
}

// build adds the steps of the case to pipeline.
func build(steps []any, pipeline *codeupipe.Pipeline) error {
	for _, item := range steps {
		spec, ok := item.(map[string]any)
		if !ok {
			return unsupported("a step is not an object")
		}
		kind, err := text(spec, "kind")
		if err != nil {
			return err
		}
		switch kind {
		case "filter":
			filter, err := filterOf(spec)
			if err != nil {
				return err
			}
			pipeline.AddFilter(filter)
		case "tap":
			tap, err := tapOf(spec)
			if err != nil {
				return err
			}
			pipeline.AddTap(tap)
		case "valve":
			when, err := object(spec, "when")
			if err != nil {
				return err
			}
			predicate, err := predicateOf(when)
			if err != nil {
				return err
			}
			gated, err := object(spec, "filter")
			if err != nil {
				return err
			}
			filter, err := filterOf(gated)
			if err != nil {
				return err
			}
			pipeline.AddValve(predicate, filter)
		case "pipeline":
			inner := codeupipe.NewNamedPipeline(cup_ops.NestedPipeline{})
			steps, err := stepsOf(spec)
			if err != nil {
				return err
			}
			if err := build(steps, inner); err != nil {
				return err
			}
			pipeline.AddPipeline(inner)
		default:
			return unsupported(fmt.Sprintf("unknown step kind '%s'", kind))
		}
	}
	return nil
}

// namesByLabel maps each label to the step name of the case. The cases name
// their steps, and the runtime reports labels (conformance/API.md). The
// steps are added in the order of the case, so the two lists are side by
// side. A label that the runtime reports and that is not in this map stays
// as it is, and fails the comparison.
func namesByLabel(pipeline *codeupipe.Pipeline, steps []any) func(string) string {
	names := make(map[string]string)
	for i, label := range pipeline.Labels() {
		spec, _ := steps[i].(map[string]any)
		name, _ := spec["name"].(string)
		names[label] = name
	}
	return func(label string) string {
		if name, ok := names[label]; ok {
			return name
		}
		return label
	}
}

func named(labels []string, name func(string) string) []any {
	out := make([]any, len(labels))
	for i, label := range labels {
		out[i] = name(label)
	}
	return out
}

func report(state *codeupipe.State, name func(string) string) map[string]any {
	var errors []string
	for _, failure := range state.Errors() {
		errors = append(errors, failure.Label)
	}
	return map[string]any{
		"executed": named(state.Executed(), name),
		"skipped":  named(state.Skipped(), name),
		"errors":   named(errors, name),
	}
}

func runCase(spec map[string]any) (map[string]any, error) {
	ctx := context.Background()
	steps, err := stepsOf(spec)
	if err != nil {
		return nil, err
	}
	pipeline := codeupipe.NewPipeline()
	if err := build(steps, pipeline); err != nil {
		return nil, err
	}
	name := namesByLabel(pipeline, steps)
	hooks := spec["hooks"] == true
	var events []string
	if hooks {
		pipeline.UseHook(cup_ops.RecordHook{Events: &events})
	}

	// A run_again step runs this pipeline again, as the TypeScript and Rust
	// runners do.
	cup_ops.SetRunAgain(func(ctx context.Context, input map[string]any) error {
		state := codeupipe.NewState()
		_, err := pipeline.RunWithState(ctx, codeupipe.NewPayload(input), state)
		cup_ops.KeepInnerState(state)
		return err
	})
	defer cup_ops.SetRunAgain(nil)

	data, err := object(spec, "input")
	if err != nil {
		return nil, err
	}
	input := codeupipe.NewPayload(data)
	result := map[string]any{"id": spec["id"]}
	// With "given_state", the caller gives the State of the run. If not, the
	// run makes one.
	var given *codeupipe.State
	var output *codeupipe.Payload
	if spec["given_state"] == true {
		given = codeupipe.NewState()
		output, err = pipeline.RunWithState(ctx, input, given)
	} else {
		output, err = pipeline.Run(ctx, input)
	}
	if err != nil {
		result["error"] = err.Error()
	} else {
		result["output"] = output.ToDict()
	}
	last := pipeline.State()
	if given == nil {
		given = last
	}
	result["state"] = report(given, name)
	result["pipeline_state"] = report(last, name)
	inner := []any{}
	for _, state := range cup_ops.TakeInnerStates() {
		inner = append(inner, report(state, name))
	}
	result["inner_states"] = inner
	result["taps"] = cup_ops.TakeTaps()
	if hooks {
		reported := make([]any, len(events))
		for i, event := range events {
			kind, label, _ := strings.Cut(event, ":")
			if label != "" {
				label = name(label)
			}
			reported[i] = kind + ":" + label
		}
		result["hooks"] = reported
	}
	result["input_after"] = input.ToDict()
	return result, nil
}

func benchCase(spec map[string]any) (map[string]any, error) {
	steps, err := stepsOf(spec)
	if err != nil {
		return nil, err
	}
	pipeline := codeupipe.NewPipeline()
	if err := build(steps, pipeline); err != nil {
		return nil, err
	}
	if spec["hooks"] == "noop" {
		pipeline.UseHook(cup_ops.NoopHook{})
	}
	data, err := object(spec, "input")
	if err != nil {
		return nil, err
	}
	return bench(spec["id"], pipeline, codeupipe.NewPayload(data)), nil
}

func main() {
	target := ""
	if len(os.Args) > 1 {
		target = os.Args[1]
	}
	var play func(map[string]any) (map[string]any, error)
	switch target {
	case "run":
		play = runCase
	case "bench:run":
		play = benchCase
	default:
		fmt.Fprintf(os.Stderr, "unknown target '%s'. The targets are: run, bench:run\n", target)
		os.Exit(2)
	}
	text, err := io.ReadAll(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, "cannot read the cases:", err)
		os.Exit(2)
	}
	var cases []any
	if err := json.Unmarshal(text, &cases); err != nil {
		fmt.Fprintln(os.Stderr, "cannot read the cases:", err)
		os.Exit(2)
	}

	results := make([]any, 0, len(cases))
	for _, item := range cases {
		cup_ops.TakeTaps()
		spec, ok := item.(map[string]any)
		if !ok {
			fmt.Fprintln(os.Stderr, "a case is not an object")
			os.Exit(2)
		}
		result, err := play(spec)
		if reason, ok := err.(unsupported); ok {
			result = map[string]any{"id": spec["id"], "unsupported": string(reason)}
		} else if err != nil {
			fmt.Fprintln(os.Stderr, "cannot play a case:", err)
			os.Exit(2)
		}
		results = append(results, result)
	}
	out := json.NewEncoder(os.Stdout)
	out.SetEscapeHTML(false)
	if err := out.Encode(results); err != nil {
		fmt.Fprintln(os.Stderr, "cannot write the results:", err)
		os.Exit(2)
	}
}
