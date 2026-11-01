package main

import (
	"context"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
	"gopkg.in/yaml.v3"
)

// duplicateKey is the error of the YAML reader for a key two times in one
// mapping.
var duplicateKey = regexp.MustCompile(`line (\d+): mapping key "(.*)" already defined`)

// ReadLayoutFilter gives the layout file as data (ADD.md, "The YAML reader").
//
// Go has no YAML reader in its standard library, so the command reads YAML
// with gopkg.in/yaml.v3, and JSON with the same reader: JSON is YAML.
//
// Filter (sync).
//
// Input keys: “root“ and “layout_path“ (relative to the root).
// Output keys: “layout“ (a map[string]any). A file that cannot be read, a
// key two times in one mapping, or a layout that is not a mapping is
// refused with exit code 2.
type ReadLayoutFilter struct{}

// Call reads and decodes the file.
func (ReadLayoutFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	path := stringOf(payload, "layout_path")
	text, err := os.ReadFile(filepath.Join(stringOf(payload, "root"), path))
	if err != nil {
		return &Refusal{ExitCode: 2, Message: "The layout " + path + " cannot be read: " + err.Error()}
	}
	var layout any
	if err := yaml.Unmarshal(text, &layout); err != nil {
		if found := duplicateKey.FindStringSubmatch(err.Error()); found != nil {
			return &Refusal{ExitCode: 2, Message: "The layout " + path + ", line " + found[1] + " has the key " +
				found[2] + " two times in one mapping. Keep one."}
		}
		return &Refusal{ExitCode: 2, Message: "The layout " + path + " cannot be read: " +
			strings.TrimPrefix(err.Error(), "yaml: ")}
	}
	mapping, isMapping := layout.(map[string]any)
	if !isMapping {
		return &Refusal{ExitCode: 2, Message: "The layout " + path +
			" is not a mapping. It starts with keys such as lang: and components:."}
	}
	payload.Insert("layout", mapping)
	return nil
}
