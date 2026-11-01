package main

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// layoutLang is the language of this command: a layout for another one is
// refused.
const layoutLang = "go"

// layoutKeys and componentKeys are the keys of the contract (ADD.md, "The
// keys"), in the order that a message gives them.
var (
	layoutKeys    = []string{"lang", "root", "components"}
	componentKeys = []string{"kind", "name", "description", "steps", "hooks"}
)

// CheckLayoutFilter checks the keys of the layout, and the shape of each.
//
// Filter (sync).
//
// Input keys: “layout“.
// Output keys: “directory“ (“root:“, or “.“) and “components“ (a
// []LaidOut, in the order of the file). A key that is not known, a key that
// is missing, or a value of the wrong shape is refused with exit code 2.
// The names are checked by the next steps.
type CheckLayoutFilter struct{}

// Call checks the layout, then each component.
func (CheckLayoutFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	layout, _ := payload.Get("layout").(map[string]any)
	if err := knownKeys(layout, layoutKeys, "the layout"); err != nil {
		return err
	}
	lang, hasLang := layout["lang"]
	if !hasLang {
		return &Refusal{ExitCode: 2, Message: "The layout has no lang:. For this command it is lang: " + layoutLang + "."}
	}
	if lang != layoutLang {
		return &Refusal{ExitCode: 2, Message: fmt.Sprintf("The layout is for %v, and this is codeupipe add for %s.", lang, layoutLang)}
	}
	directory := "."
	if root, given := layout["root"]; given {
		text, isText := root.(string)
		if !isText || text == "" {
			return &Refusal{ExitCode: 2, Message: "root: is a directory, such as src/pricing."}
		}
		directory = text
	}
	listed, _ := layout["components"].([]any)
	if len(listed) == 0 {
		return &Refusal{ExitCode: 2, Message: "components: is a list with one component or more, each with kind: and name:."}
	}
	components := make([]LaidOut, 0, len(listed))
	for _, item := range listed {
		component, err := laidOutOf(item)
		if err != nil {
			return err
		}
		components = append(components, component)
	}
	payload.Insert("directory", directory).Insert("components", components)
	return nil
}

// knownKeys refuses a key of mapping that is not one of keys.
func knownKeys(mapping map[string]any, keys []string, label string) error {
	unknown := []string{}
	for key := range mapping {
		if !contains(keys, key) {
			unknown = append(unknown, key)
		}
	}
	if len(unknown) == 0 {
		return nil
	}
	sort.Strings(unknown)
	return &Refusal{ExitCode: 2, Message: "Unknown key " + strings.Join(unknown, ", ") + " in " + label +
		". The keys are: " + strings.Join(keys, ", ") + "."}
}

// laidOutOf checks one component of the list.
func laidOutOf(item any) (LaidOut, error) {
	mapping, isMapping := item.(map[string]any)
	if !isMapping {
		return LaidOut{}, &Refusal{ExitCode: 2, Message: fmt.Sprintf("A component is a mapping with kind: and name:, not %v.", item)}
	}
	label := "the component with no name"
	if name, isText := mapping["name"].(string); isText {
		label = "the component " + name
	}
	if err := knownKeys(mapping, componentKeys, label); err != nil {
		return LaidOut{}, err
	}
	for _, key := range []string{"kind", "name"} {
		if _, isText := mapping[key].(string); !isText {
			return LaidOut{}, &Refusal{ExitCode: 2, Message: "T" + label[1:] + " has no " + key + ":."}
		}
	}
	component := LaidOut{Kind: mapping["kind"].(string), Name: mapping["name"].(string)}
	if description, given := mapping["description"]; given {
		text, isText := description.(string)
		if !isText {
			return LaidOut{}, &Refusal{ExitCode: 2, Message: "The description of " + label + " is not a text."}
		}
		component.Description = text
	}
	for _, key := range []string{"steps", "hooks"} {
		if _, given := mapping[key]; given && component.Kind != "pipeline" {
			return LaidOut{}, &Refusal{ExitCode: 2, Message: key + ": is only for a pipeline, and " + component.Name +
				" is a " + component.Kind + "."}
		}
	}
	if steps, given := mapping["steps"]; given {
		list, isList := steps.([]any)
		if !isList {
			return LaidOut{}, &Refusal{ExitCode: 2, Message: "The steps of " + component.Name +
				" are a list. A step is a name, or valve: [Predicate, Filter]."}
		}
		for _, step := range list {
			read, readable := layoutStepOf(step)
			if !readable {
				return LaidOut{}, &Refusal{ExitCode: 2, Message: fmt.Sprintf(
					"The step %v of %s cannot be read. A step is a name, or valve: [Predicate, Filter].", step, component.Name)}
			}
			component.Steps = append(component.Steps, read)
		}
	}
	if hooks, given := mapping["hooks"]; given {
		list, isList := hooks.([]any)
		for _, hook := range list {
			name, isText := hook.(string)
			if !isText {
				isList = false
				break
			}
			component.Hooks = append(component.Hooks, name)
		}
		if !isList {
			return LaidOut{}, &Refusal{ExitCode: 2, Message: "The hooks of " + component.Name + " are a list of names."}
		}
	}
	return component, nil
}

// layoutStepOf reads a name, or a mapping with only “valve“, whose value is
// two names.
func layoutStepOf(step any) (LayoutStep, bool) {
	if name, isText := step.(string); isText {
		return LayoutStep{Name: name}, true
	}
	mapping, isMapping := step.(map[string]any)
	if !isMapping || len(mapping) != 1 {
		return LayoutStep{}, false
	}
	pair, isList := mapping["valve"].([]any)
	if !isList || len(pair) != 2 {
		return LayoutStep{}, false
	}
	predicate, isText := pair[0].(string)
	filter, isText2 := pair[1].(string)
	if !isText || !isText2 {
		return LayoutStep{}, false
	}
	return LayoutStep{Predicate: predicate, Filter: filter}, true
}

// contains says that list has s.
func contains(list []string, s string) bool {
	for _, item := range list {
		if item == s {
			return true
		}
	}
	return false
}
