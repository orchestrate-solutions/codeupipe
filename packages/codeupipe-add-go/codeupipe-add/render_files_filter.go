package main

import (
	"context"
	"os"
	"path/filepath"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// RenderFilesFilter gives the text of the two files.
//
// Filter (sync).
//
// Input keys: “kind“, “type_name“, “snake“, “package_name“,
// “module“, “description“.
// Output keys: “component_text“ and “test_text“. With no description, the
// header says “TODO: say what <type_name> does.“
type RenderFilesFilter struct{}

// Call fills the template of the kind, and the template of the test.
func (RenderFilesFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	kind := stringOf(payload, "kind")
	template, known := components[kind]
	if !known {
		return &Refusal{ExitCode: 2, Message: "The kind " + quote(kind) + " has no component in Go."}
	}
	typeName := stringOf(payload, "type_name")
	description := stringOf(payload, "description")
	if description == "" {
		description = "TODO: say what " + typeName + " does."
	}
	values := map[string]string{
		"type_name":    typeName,
		"description":  description,
		"package_name": stringOf(payload, "package_name"),
		"snake":        stringOf(payload, "snake"),
		"module":       moduleOf(payload),
	}
	// The test is beside the component, in the package of the component, so it
	// needs no import: a test cannot import its own package.
	payload.Insert("component_text", fill(template, values)).
		Insert("test_text", fill(testTemplateSame, values))
	return nil
}

// fill replaces each {key} in the template with its value.
func fill(template string, values map[string]string) string {
	for key, value := range values {
		template = strings.ReplaceAll(template, "{"+key+"}", value)
	}
	return template
}

// moduleImport gives the path that the test of a root package imports: the
// module of the project, or "" with none, which means the directory itself.
func moduleImport(module string) string {
	if module == "" {
		return ""
	}
	return module
}

// ModuleOfGoMod gives the module of the text of a go.mod, or "" when it has
// none. It is the text of the “module“ line, without its spaces and its
// quotes.
func ModuleOfGoMod(text string) string {
	for _, line := range strings.Split(text, "\n") {
		fields := strings.Fields(strings.TrimSuffix(line, "\r"))
		if len(fields) >= 2 && fields[0] == "module" {
			return unquote(fields[1])
		}
	}
	return ""
}

// unquote takes the quotes off a Go string, when it has them.
func unquote(s string) string {
	if len(s) < 2 {
		return s
	}
	if s[0] == '"' && s[len(s)-1] == '"' || s[0] == '`' && s[len(s)-1] == '`' {
		return s[1 : len(s)-1]
	}
	return s
}

// moduleOfGoMod gives the module of the text of a go.mod, or "" when it has
// none. It is the text of the “module“ line, without its spaces and its
// quotes.
func moduleOfGoMod(text string) string {
	for _, line := range strings.Split(text, "\n") {
		fields := strings.Fields(strings.TrimSuffix(line, "\r"))
		if len(fields) >= 2 && fields[0] == "module" {
			return unquote(fields[1])
		}
	}
	return ""
}

// importDir gives the path that the test of the component imports: the module
// of the project with the directory of the component and its file after it.
// The test is beside the component, so a test in the same package needs no
// import at all: the empty string says so.
func importDir(module, dir, snake string) string {
	if module == "" || dir == "" {
		return ""
	}
	return module + "/" + dir + "/" + snake
}

// moduleOf gives the module of the project: the module key when the caller
// read one, or the module line of the go.mod in the root. A project with no
// go.mod, or without a module line, has no module.
func moduleOf(payload *codeupipe.Payload) string {
	if module := stringOf(payload, "module"); module != "" {
		return module
	}
	text, err := os.ReadFile(filepath.Join(stringOf(payload, "root"), "go.mod"))
	if err != nil {
		return ""
	}
	return moduleOfGoMod(string(text))
}
