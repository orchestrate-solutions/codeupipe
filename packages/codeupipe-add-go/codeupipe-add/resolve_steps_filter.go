package main

import (
	"context"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// stepCalls gives the call of each kind of step (ADD.md, "The steps").
var stepCalls = map[string]string{"filter": "AddFilter", "tap": "AddTap", "pipeline": "AddPipeline"}

// ResolveStepsFilter gives the calls of each pipeline of the layout, steps
// first, then hooks. The components of a layout are in one directory, so in
// one package: a pipeline needs no import for its steps.
//
// Filter (sync).
//
// Input keys: “components“ (named).
// Output keys: “components“, each with Calls. A name that is not a
// component, a step of the wrong kind, or a pipeline that has itself as a
// step is refused with exit code 2.
type ResolveStepsFilter struct{}

// Call resolves each pipeline, then refuses a loop.
func (ResolveStepsFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	components, _ := payload.Get("components").([]LaidOut)
	resolved := make([]LaidOut, 0, len(components))
	for _, component := range components {
		calls, err := callsOf(component, components)
		if err != nil {
			return err
		}
		component.Calls = calls
		resolved = append(resolved, component)
	}
	for _, component := range resolved {
		if err := refuseALoop(component, resolved, nil); err != nil {
			return err
		}
	}
	payload.Insert("components", resolved)
	return nil
}

// findComponent gives the component that name (its name or its type name) is.
func findComponent(name string, all []LaidOut, of LaidOut) (LaidOut, error) {
	for _, used := range all {
		if used.Name == name || used.TypeName == name {
			return used, nil
		}
	}
	return LaidOut{}, &Refusal{ExitCode: 2, Message: name + ", a step of " + of.Name + ", is not a component of the layout."}
}

// callsOf gives the calls of one pipeline.
func callsOf(component LaidOut, all []LaidOut) ([]LayoutCall, error) {
	calls := []LayoutCall{}
	for _, step := range component.Steps {
		if step.Name == "" {
			pair := []string{}
			for i, name := range []string{step.Predicate, step.Filter} {
				used, err := findComponent(name, all, component)
				if err != nil {
					return nil, err
				}
				wanted := []string{"predicate", "filter"}[i]
				if used.Kind != wanted {
					return nil, &Refusal{ExitCode: 2, Message: "valve: [" + step.Predicate + ", " + step.Filter + "] in " +
						component.Name + ": a valve is [Predicate, Filter], and " + used.Name + " is a " + used.Kind +
						", not a " + wanted + "."}
				}
				pair = append(pair, used.TypeName)
			}
			calls = append(calls, LayoutCall{Method: "AddValve", Types: pair})
			continue
		}
		used, err := findComponent(step.Name, all, component)
		if err != nil {
			return nil, err
		}
		switch used.Kind {
		case "predicate":
			return nil, &Refusal{ExitCode: 2, Message: used.Name + " is a predicate. A predicate is not a step: put it in a valve: [" +
				used.Name + ", Filter]."}
		case "hook":
			return nil, &Refusal{ExitCode: 2, Message: used.Name + " is a hook. A hook is not a step: put it in hooks: of " +
				component.Name + "."}
		}
		calls = append(calls, LayoutCall{Method: stepCalls[used.Kind], Types: []string{used.TypeName}})
	}
	for _, name := range component.Hooks {
		hook, err := findComponent(name, all, component)
		if err != nil {
			return nil, err
		}
		if hook.Kind != "hook" {
			return nil, &Refusal{ExitCode: 2, Message: name + " in the hooks of " + component.Name + " is a " + hook.Kind + ", not a hook."}
		}
		calls = append(calls, LayoutCall{Method: "UseHook", Types: []string{hook.TypeName}})
	}
	return calls, nil
}

// refuseALoop refuses a pipeline that is a step of itself, through its
// nested pipelines.
func refuseALoop(component LaidOut, all []LaidOut, path []string) error {
	for i, typeName := range path {
		if typeName == component.TypeName {
			loop := append(append([]string{}, path[i:]...), component.TypeName)
			return &Refusal{ExitCode: 2, Message: "A pipeline has itself as a step: " + strings.Join(loop, " -> ") + "."}
		}
	}
	for _, call := range component.Calls {
		if call.Method != "AddPipeline" {
			continue
		}
		for _, nested := range all {
			if nested.TypeName == call.Types[0] {
				if err := refuseALoop(nested, all, append(append([]string{}, path...), component.TypeName)); err != nil {
					return err
				}
			}
		}
	}
	return nil
}
