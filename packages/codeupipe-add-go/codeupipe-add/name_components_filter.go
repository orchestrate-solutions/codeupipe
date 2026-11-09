package main

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// NameComponentsFilter gives the type name and the paths of each component,
// as phase 1 gives them: it uses the Filters of phase 1.
//
// Filter (sync).
//
// Input keys: “root“, “directory“ and “components“.
// Output keys: “components“, each with TypeName, Snake, ComponentPath,
// TestPath and PackageName. A name that phase 1 refuses, or two components
// with the same type name, are refused with exit code 2.
type NameComponentsFilter struct{}

// Call names each component.
func (NameComponentsFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	components, _ := payload.Get("components").([]LaidOut)
	named := make([]LaidOut, 0, len(components))
	seen := map[string]string{}
	for _, component := range components {
		one := codeupipe.NewPayload(map[string]any{"root": stringOf(payload, "root"),
			"directory": stringOf(payload, "directory"), "kind": component.Kind, "name": component.Name})
		if err := (TypeNameFilter{}).Call(ctx, one); err != nil {
			return err
		}
		if err := (PlanFilesFilter{}).Call(ctx, one); err != nil {
			return err
		}
		typeName := stringOf(one, "type_name")
		if first, twice := seen[typeName]; twice {
			return &Refusal{ExitCode: 2, Message: "Two components are " + typeName + ": " + first + " and " + component.Name + "."}
		}
		seen[typeName] = component.Name
		component.TypeName = typeName
		component.Snake = stringOf(one, "snake")
		component.ComponentPath = stringOf(one, "component_path")
		component.TestPath = stringOf(one, "test_path")
		component.PackageName = stringOf(one, "package_name")
		named = append(named, component)
	}
	payload.Insert("components", named)
	return nil
}
