package codeupipelint

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"sort"
)

// ConfigName is the file that holds the settings of the project's tools.
const ConfigName = "cup.config.json"

// lintKeyList names the keys that the linter reads, for an error message.
const lintKeyList = "paths, exclude, disable"

// ReadLintConfig reads the lint section of the config file at path. It gives
// nil, and no error, when the file is not there. A key of the lint section
// that the linter does not read is an error, so the file cannot hold a
// setting that does nothing. Other sections of the file are for other tools.
//
// cup: allow-plain the edge of the program: it reads a file before the pipeline runs
func ReadLintConfig(path string) (*LintConfig, error) {
	text, err := os.ReadFile(path)
	if errors.Is(err, fs.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	var config any
	if err := json.Unmarshal(text, &config); err != nil {
		return nil, fmt.Errorf("%s is not valid JSON: %w", path, err)
	}
	root, ok := config.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("%s must hold a JSON object", path)
	}
	section, ok := root["lint"]
	if !ok {
		return &LintConfig{}, nil
	}
	lint, ok := section.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("%s: lint must be an object", path)
	}
	keys := make([]string, 0, len(lint))
	for key := range lint {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	out := &LintConfig{}
	for _, key := range keys {
		var slot *[]string
		switch key {
		case "paths":
			slot = &out.Paths
		case "exclude":
			slot = &out.Exclude
		case "disable":
			slot = &out.Disable
		default:
			return nil, fmt.Errorf("%s: lint: unknown key '%s' (the keys are %s)", path, key, lintKeyList)
		}
		items, isList := lint[key].([]any)
		strs := make([]string, 0, len(items))
		for _, item := range items {
			str, isString := item.(string)
			if !isString {
				isList = false
				break
			}
			strs = append(strs, str)
		}
		if !isList {
			return nil, fmt.Errorf("%s: lint.%s must be a list of strings", path, key)
		}
		*slot = strs
	}
	return out, nil
}
