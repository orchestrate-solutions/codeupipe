package codeupipelint

import (
	"context"
	"errors"
	"go/parser"
	"go/scanner"
	"go/token"
	"os"
)

// ParseFilesFilter reads and parses each file.
//
// Reads Files. Writes Sources (the files that parse, with their
// "cup: allow-..." comments), a CUP-I000 finding for a file with a syntax
// error, and Errors for a file that cannot be read.
type ParseFilesFilter struct{}

func (ParseFilesFilter) Call(ctx context.Context, run *LintRun) error {
	for _, path := range run.Files {
		bytes, err := os.ReadFile(path)
		if err != nil {
			run.Errors = append(run.Errors, err.Error())
			continue
		}
		text := string(bytes)
		fset := token.NewFileSet()
		file, err := parser.ParseFile(fset, path, text, parser.ParseComments|parser.SkipObjectResolution)
		var list scanner.ErrorList
		if errors.As(err, &list) && len(list) > 0 {
			rule, _ := RuleOf(ParseError)
			run.Findings = append(run.Findings, Finding{
				Path: path, Line: list[0].Pos.Line, Col: list[0].Pos.Column,
				Rule: ParseError, Slug: rule.Slug, Message: list[0].Msg + ". " + rule.Fix,
			})
			continue
		}
		run.Sources = append(run.Sources, Source{
			Path: path, Text: text, Fset: fset, File: file, Markers: MarkersOf(fset, file, text),
		})
	}
	return nil
}
