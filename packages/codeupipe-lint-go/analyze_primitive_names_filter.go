package codeupipelint

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"
	"unicode"
)

// AnalyzePrimitiveNamesFilter finds a primitive whose file name or type name does not fit: CUP-I006, I007.
//
// CUP-I007: the type name of a primitive ends with its role, such as Filter.
// CUP-I006: the file name is the type name in snake_case, then ".go".
//
// Checked: the primitives at the top level of a file. Not checked: the
// files whose name ends in _test.go.
//
// Reads Sources. Writes Findings.
type AnalyzePrimitiveNamesFilter struct{}

func (f AnalyzePrimitiveNamesFilter) Call(ctx context.Context, run *LintRun) error {
	for _, source := range run.Sources {
		if IsTestFile(source.Path) {
			continue
		}
		file := filepath.Base(source.Path)
		stem := strings.TrimSuffix(file, ".go")
		for _, primitive := range PrimitivesIn(source.File) {
			role := primitive.Kind.Name()
			wanted := primitive.Name
			if !strings.HasSuffix(wanted, role) {
				wanted += role
				what := fmt.Sprintf("%s `%s` does not say what it is. Name it `%s`", role, primitive.Name, wanted)
				run.Findings = append(run.Findings, MakeFinding(source, primitive.Pos, PrimitiveRoleSuffix, what, 0))
			}
			snake := f.snakeCase(wanted)
			if stem != snake {
				what := fmt.Sprintf("`%s` is in `%s`. Put it in `%s.go`", wanted, file, snake)
				run.Findings = append(run.Findings, MakeFinding(source, primitive.Pos, PrimitiveFileName, what, 0))
			}
		}
	}
	return nil
}

// snakeCase gives the snake_case of a type name: "DiscountFilter" gives
// "discount_filter". A run of capitals is one word, and its last capital
// starts the next word when a small letter follows it: "HTTPGetFilter"
// gives "http_get_filter". A capital after a digit starts a word too:
// "V2Filter" gives "v2_filter".
func (AnalyzePrimitiveNamesFilter) snakeCase(name string) string {
	runes := []rune(name)
	var out strings.Builder
	for index, r := range runes {
		startsWord := false
		if index > 0 && unicode.IsUpper(r) {
			before := runes[index-1]
			hasAfter := index+1 < len(runes)
			switch {
			case unicode.IsLower(before), unicode.IsDigit(before):
				startsWord = true
			case unicode.IsUpper(before) && hasAfter && unicode.IsLower(runes[index+1]):
				startsWord = true
			}
		}
		if startsWord {
			out.WriteRune('_')
		}
		out.WriteRune(unicode.ToLower(r))
	}
	return out.String()
}
