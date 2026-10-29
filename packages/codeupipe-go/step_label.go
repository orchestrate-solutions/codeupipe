package codeupipe

import (
	"reflect"
	"strings"
)

// labelOf gives the label of a step: the name of its type. For a pointer it
// is the type that it points to, and type arguments are dropped
// (Wrapper[pkg.Inner] gives Wrapper). A type with no name gives "anonymous".
// State and Hooks report a step by this label.
func labelOf(step any) string {
	t := reflect.TypeOf(step)
	for t != nil && t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	if t == nil {
		return "anonymous"
	}
	name := t.Name()
	if open := strings.IndexByte(name, '['); open >= 0 {
		name = name[:open]
	}
	if name == "" {
		return "anonymous"
	}
	return name
}
