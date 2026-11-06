package codeupipelint

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// writeConfig writes text into a new directory as cup.config.json, and gives
// the path of the file.
func writeConfig(t *testing.T, text string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), ConfigName)
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

// wantError fails the test when err is nil or does not hold text.
func wantError(t *testing.T, err error, text string) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), text) {
		t.Fatalf("error %v, want one with %q", err, text)
	}
}

func TestConfigNameIsCupConfigJSON(t *testing.T) {
	if ConfigName != "cup.config.json" {
		t.Fatalf("ConfigName %q", ConfigName)
	}
}

func TestAMissingFileGivesNoConfigAndNoError(t *testing.T) {
	config, err := ReadLintConfig(filepath.Join(t.TempDir(), ConfigName))
	if err != nil || config != nil {
		t.Fatalf("config %v, error %v", config, err)
	}
}

func TestTheLintSectionIsRead(t *testing.T) {
	path := writeConfig(t, `{"lint": {"paths": ["."], "exclude": ["*/gen/*"], "disable": ["CUP-I006"]}, "deploy": {"anything": true}}`)
	config, err := ReadLintConfig(path)
	if err != nil {
		t.Fatal(err)
	}
	got := fmt.Sprintf("%q %q %q", config.Paths, config.Exclude, config.Disable)
	if want := `["."] ["*/gen/*"] ["CUP-I006"]`; got != want {
		t.Fatalf("got %s, want %s", got, want)
	}
}

func TestAFileWithoutALintSectionGivesAnEmptyConfig(t *testing.T) {
	config, err := ReadLintConfig(writeConfig(t, `{"deploy": {}}`))
	if err != nil || config == nil {
		t.Fatalf("config %v, error %v", config, err)
	}
	if config.Paths != nil || config.Exclude != nil || config.Disable != nil {
		t.Fatalf("config %+v, want no lists", *config)
	}
}

func TestAKeyThatTheLinterDoesNotReadIsAnError(t *testing.T) {
	_, err := ReadLintConfig(writeConfig(t, `{"lint": {"path": ["."]}}`))
	wantError(t, err, "unknown key 'path'")
}

func TestAListOfStringsIsChecked(t *testing.T) {
	cases := map[string]string{
		`{"lint": {"paths": "."}}`:    "lint.paths must be a list of strings",
		`{"lint": {"exclude": [1]}}`:  "lint.exclude must be a list of strings",
		`{"lint": {"disable": null}}`: "lint.disable must be a list of strings",
		`{"lint": {"paths": [null]}}`: "lint.paths must be a list of strings",
		`{"lint": "."}`:               "lint must be an object",
		`[]`:                          "must hold a JSON object",
		`{"lint": `:                   "is not valid JSON",
	}
	for text, want := range cases {
		_, err := ReadLintConfig(writeConfig(t, text))
		wantError(t, err, want)
	}
}
