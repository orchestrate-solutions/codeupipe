package main

// The text of each file that ``codeupipe add`` makes for Go. {type_name},
// {description}, {package_name}, {snake} and {module} are filled in by
// RenderFilesFilter. Each component does nothing (conformance/ADD.md), and
// the test fails on purpose, with the message of the contract.
//
// The test of a root package has no import when the project has no go.mod
// with a module: the test is in the package of the component itself, as a
// user's test would be. {module} is empty then, and the template that
// RenderFilesFilter chooses has no import line.

// components is the template of the component file for each kind.
var components = map[string]string{
	"filter": `// {type_name}: {description}
package {package_name}

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// {type_name} is a Filter: it gives the Payload back with no change.
type {type_name} struct{}

// Call returns the Payload with no change.
func ({type_name}) Call(ctx context.Context, payload *codeupipe.Payload) error {
	return nil
}
`,
	"predicate": `// {type_name}: {description}
package {package_name}

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// {type_name} is a Predicate: its answer is always no.
type {type_name} struct{}

// Test answers no for every Payload.
func ({type_name}) Test(ctx context.Context, payload *codeupipe.Payload) bool {
	return false
}
`,
	"tap": `// {type_name}: {description}
package {package_name}

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// {type_name} is a Tap: it reads nothing yet.
type {type_name} struct{}

// Observe does nothing.
func ({type_name}) Observe(ctx context.Context, payload *codeupipe.Payload) error {
	return nil
}
`,
	"hook": `// {type_name}: {description}
package {package_name}

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// {type_name} is a Hook: it does nothing at each event.
type {type_name} struct {
	codeupipe.HookBase
}

// Before does nothing at the start of a step.
func ({type_name}) Before(ctx context.Context, step string, payload *codeupipe.Payload) {
}

// After does nothing at the end of a step.
func ({type_name}) After(ctx context.Context, step string, payload *codeupipe.Payload) {
}

// OnError does nothing when a step fails.
func ({type_name}) OnError(ctx context.Context, step string, err error, payload *codeupipe.Payload) {
}
`,
	"pipeline": `// {type_name}: {description}
package {package_name}

import (
	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// {type_name} is a Pipeline with no steps yet.
type {type_name} struct{}

// AddSteps adds no step yet.
func ({type_name}) AddSteps(pipeline *codeupipe.Pipeline) {
}
`,
}

// testTemplateSame is the test file with no import: the test is beside the
// component, in the package of the component, so it needs nothing to make it.
const testTemplateSame = `// The acceptance case of {type_name}.
package {package_name}

import (
	"testing"
)

func Test{type_name}(t *testing.T) {
	if (&{type_name}{}) == nil {
		t.Fatal("Write the acceptance case for {type_name}.")
	}
	t.Fatal("Write the acceptance case for {type_name}.")
}
`
