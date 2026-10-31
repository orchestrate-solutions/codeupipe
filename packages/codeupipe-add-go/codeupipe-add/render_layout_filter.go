package main

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// RenderLayoutFilter gives the text of the two files of each component of
// the layout. It uses the RenderFilesFilter of phase 1, which writes the
// steps of a pipeline when it has calls.
//
// Filter (sync).
//
// Input keys: “root“ and “components“ (resolved).
// Output keys: “components“, each with ComponentText and TestText.
type RenderLayoutFilter struct{}

// Call renders each component.
func (RenderLayoutFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	components, _ := payload.Get("components").([]LaidOut)
	rendered := make([]LaidOut, 0, len(components))
	for _, component := range components {
		one := codeupipe.NewPayload(map[string]any{"root": stringOf(payload, "root"), "kind": component.Kind,
			"type_name": component.TypeName, "snake": component.Snake, "package_name": component.PackageName,
			"description": component.Description, "calls": component.Calls})
		if err := (RenderFilesFilter{}).Call(ctx, one); err != nil {
			return err
		}
		component.ComponentText = stringOf(one, "component_text")
		component.TestText = stringOf(one, "test_text")
		rendered = append(rendered, component)
	}
	payload.Insert("components", rendered)
	return nil
}
