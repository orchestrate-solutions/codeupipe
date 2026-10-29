package main

import (
	"context"
	"strings"
	"unicode"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// roles is the suffix that each kind adds to the type name.
var roles = map[string]string{
	"filter":    "Filter",
	"predicate": "Predicate",
	"tap":       "Tap",
	"hook":      "Hook",
	"pipeline":  "Pipeline",
}

// notMade are the kinds that “add“ does not make, with why (ADD.md).
var notMade = map[string]string{
	"valve":   "A Valve is not a type. Make a Predicate and a Filter, and join them with add_valve(predicate, filter).",
	"payload": "The runtime makes the Payload. A user does not write one.",
	"state":   "The runtime makes the State. A user does not write one.",
}

// TypeNameFilter makes the type name from the kind and the name: the words of
// the name with a capital each, and the role of the kind at the end.
//
// Filter (sync).
//
// Input keys: “kind“, “name“.
// Output keys: “type_name“ (“DiscountFilter“) and “snake“
// (“discount_filter“), the file name by the rule of the linters
// (CUP-I006). A kind or a name that cannot be used is refused with exit
// code 2.
type TypeNameFilter struct{}

// Call checks the kind and the name, and gives the two names.
func (TypeNameFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	kind, _ := payload.Get("kind").(string)
	name, _ := payload.Get("name").(string)
	if why, refused := notMade[kind]; refused {
		return &Refusal{ExitCode: 2, Message: why}
	}
	role, known := roles[kind]
	if !known {
		return &Refusal{ExitCode: 2, Message: "Unknown kind " + quote(kind) +
			". The kinds are: filter, predicate, tap, hook, pipeline."}
	}
	if !usableName(name) {
		return &Refusal{ExitCode: 2, Message: "The name " + quote(name) +
			" cannot be used. A name starts with a letter, and has only letters, digits, _ and -."}
	}
	typeName := pascal(name)
	if !strings.HasSuffix(typeName, role) {
		typeName += role
	}
	payload.Insert("type_name", typeName).Insert("snake", snakeCase(typeName))
	return nil
}

// usableName says whether a name can be used: it starts with a letter and
// has only letters, digits, _ and -.
func usableName(name string) bool {
	if name == "" || !isLetter(rune(name[0])) {
		return false
	}
	for _, r := range name {
		if !isLetter(r) && !unicode.IsDigit(r) && r != '_' && r != '-' {
			return false
		}
	}
	return true
}

func isLetter(r rune) bool {
	return (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z')
}

// pascal makes the words of the name PascalCase: each _ and - starts a new
// word, and the first letter of each word becomes a capital.
func pascal(name string) string {
	var out strings.Builder
	capital := true
	for _, r := range name {
		if r == '_' || r == '-' {
			capital = true
			continue
		}
		if capital {
			out.WriteRune(unicode.ToUpper(r))
			capital = false
			continue
		}
		out.WriteRune(r)
	}
	return out.String()
}

// snakeCase is the rule of the linters (CUP-I006): a word starts before a
// capital that follows a small letter or a digit, and before a capital that
// is followed by a small letter and follows a capital. The words are joined
// with _ in small letters: HTTPGetFilter gives http_get_filter.
func snakeCase(typeName string) string {
	runes := []rune(typeName)
	var out strings.Builder
	for i, r := range runes {
		if i > 0 && unicode.IsUpper(r) && startsWord(runes, i) {
			out.WriteRune('_')
		}
		out.WriteRune(unicode.ToLower(r))
	}
	return out.String()
}

func startsWord(runes []rune, i int) bool {
	before := runes[i-1]
	if unicode.IsLower(before) || unicode.IsDigit(before) {
		return true
	}
	// A capital that follows a capital starts a word only when a small
	// letter follows it: HTTPGet gives HTTP and Get.
	return unicode.IsUpper(before) && i+1 < len(runes) && unicode.IsLower(runes[i+1])
}

// quote puts a string in double quotes, as the Python command shows it.
func quote(s string) string {
	return `"` + strings.ReplaceAll(s, `"`, `\"`) + `"`
}
