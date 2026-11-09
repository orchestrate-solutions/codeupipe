package main

import (
	"context"
	"os"
	"path/filepath"
	"reflect"
	"regexp"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

var (
	// stepCall is a call of a step of a pipeline.
	stepCall = regexp.MustCompile(`\.(AddFilter|AddValve|AddTap|AddPipeline|UseHook)\(`)
	// stepType is a type in a call: a composite literal (“DiscountFilter{“)
	// or a function (“NewNamedPipeline(“). A field (“Rate:“) is not one.
	stepType = regexp.MustCompile(`\b([A-Z]\w*)\s*[{(]`)
	// goComment is a comment of Go.
	goComment = regexp.MustCompile(`//[^\n]*|/\*(?s:.*?)\*/`)
)

// StalePipelinesFilter finds a kept pipeline file whose steps are not those
// of the layout.
//
// Filter (sync).
//
// Input keys: “root“, “components“ and “kept“.
// Output keys: “stale“: the path of each kept pipeline file whose steps
// (the method and the types of each call, in order) are not those that the
// layout gives. The arguments and the comments do not count, so a file that
// a user filled in is not stale while its steps are the same.
type StalePipelinesFilter struct{}

// Call compares the steps of each kept pipeline file with those of the layout.
func (StalePipelinesFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	root := stringOf(payload, "root")
	kept, _ := payload.Get("kept").([]string)
	components, _ := payload.Get("components").([]LaidOut)
	stale := []string{}
	for _, component := range components {
		if component.Kind != "pipeline" || !contains(kept, component.ComponentPath) {
			continue
		}
		text, err := os.ReadFile(filepath.Join(root, component.ComponentPath))
		if err != nil || !reflect.DeepEqual(stepsOf(string(text)), stepsOf(component.ComponentText)) {
			stale = append(stale, component.ComponentPath)
		}
	}
	payload.Insert("stale", stale)
	return nil
}

// stepsOf gives the method and the types of each call of a step, in order.
func stepsOf(text string) []LayoutCall {
	code := goComment.ReplaceAllString(text, "")
	steps := []LayoutCall{}
	for _, found := range stepCall.FindAllStringSubmatchIndex(code, -1) {
		depth, end := 1, found[1]
		for depth > 0 && end < len(code) {
			switch code[end] {
			case '(':
				depth++
			case ')':
				depth--
			}
			end++
		}
		types := []string{}
		for _, match := range stepType.FindAllStringSubmatch(code[found[1]:end], -1) {
			types = append(types, match[1])
		}
		steps = append(steps, LayoutCall{Method: code[found[2]:found[3]], Types: types})
	}
	return steps
}
