package codeupipelint

import (
	"context"
	"fmt"
	"go/ast"
	"go/token"
	"slices"
)

// The methods of the Payload that write to it.
var payloadWrites = []string{"Insert", "Remove", "Merge", "WithTrace", "Stamp"}

// AnalyzePayloadWritesFilter finds a Tap, a Predicate or a Hook that writes to its payload: CUP-I004.
//
// In the body of a Predicate's Test, a Tap's Observe, and a Hook's Before,
// After and OnError, it flags a call of a write method of the payload (the
// last parameter), and an assignment or ++ or -- whose left side starts at
// the payload. A chain of writes is one finding, at its first call. A
// function literal with a parameter of the same name is another value.
//
// Reads Sources. Writes Findings.
type AnalyzePayloadWritesFilter struct{}

func (f AnalyzePayloadWritesFilter) Call(ctx context.Context, run *LintRun) error {
	for _, source := range run.Sources {
		for _, declaration := range source.File.Decls {
			function, ok := declaration.(*ast.FuncDecl)
			if !ok || function.Recv == nil || function.Body == nil {
				continue
			}
			kind, ok := KindOfMethod(function)
			if !ok || !f.mustOnlyRead(kind) {
				continue
			}
			payload := f.payloadName(function)
			if payload == "" || payload == "_" {
				continue
			}
			run.Findings = append(run.Findings, f.writes(source, function, kind, payload)...)
		}
	}
	return nil
}

// mustOnlyRead is true for the kinds that read the payload: Predicate, Tap and Hook.
func (AnalyzePayloadWritesFilter) mustOnlyRead(kind PrimitiveKind) bool {
	return kind == PredicateKind || kind == TapKind || kind == HookKind
}

// payloadName gives the name of the last parameter, the payload, or "" when
// it has no name.
func (AnalyzePayloadWritesFilter) payloadName(function *ast.FuncDecl) string {
	params := function.Type.Params.List
	last := params[len(params)-1]
	if len(last.Names) == 0 {
		return ""
	}
	return last.Names[len(last.Names)-1].Name
}

// writes gives the writes to the payload in the body of one step method.
func (f AnalyzePayloadWritesFilter) writes(source Source, function *ast.FuncDecl, kind PrimitiveKind, payload string) []Finding {
	var found []Finding
	flag := func(pos token.Pos, code string) {
		what := fmt.Sprintf("%s `%s` writes to its payload in `%s`: `%s`",
			kind.Name(), ReceiverName(function), function.Name.Name, code)
		found = append(found, MakeFinding(source, pos, WriteOutsideFilter, what, 0))
	}
	ast.Inspect(function.Body, func(node ast.Node) bool {
		switch node := node.(type) {
		case *ast.FuncLit:
			return !f.declares(node.Type, payload)
		case *ast.CallExpr:
			selector, ok := node.Fun.(*ast.SelectorExpr)
			if !ok || !slices.Contains(payloadWrites, selector.Sel.Name) {
				return true
			}
			if base, ok := selector.X.(*ast.Ident); ok && base.Name == payload {
				flag(node.Pos(), f.text(source, node))
			}
		case *ast.AssignStmt:
			for _, left := range node.Lhs {
				if f.rootName(left) == payload {
					flag(left.Pos(), f.text(source, node))
					break
				}
			}
		case *ast.IncDecStmt:
			if f.rootName(node.X) == payload {
				flag(node.X.Pos(), f.text(source, node))
			}
		}
		return true
	})
	return found
}

// declares is true when a function type has a parameter or a result named name.
func (AnalyzePayloadWritesFilter) declares(function *ast.FuncType, name string) bool {
	for _, fields := range []*ast.FieldList{function.Params, function.Results} {
		if fields == nil {
			continue
		}
		for _, field := range fields.List {
			for _, ident := range field.Names {
				if ident.Name == name {
					return true
				}
			}
		}
	}
	return false
}

// rootName gives the variable at the start of an expression: "p" for
// p.Bulk, p.Items[0], *p and (p).Count. It is "" when there is none.
func (AnalyzePayloadWritesFilter) rootName(expr ast.Expr) string {
	for {
		switch inner := expr.(type) {
		case *ast.Ident:
			return inner.Name
		case *ast.SelectorExpr:
			expr = inner.X
		case *ast.IndexExpr:
			expr = inner.X
		case *ast.StarExpr:
			expr = inner.X
		case *ast.ParenExpr:
			expr = inner.X
		default:
			return ""
		}
	}
}

// text gives the source code of a node.
func (AnalyzePayloadWritesFilter) text(source Source, node ast.Node) string {
	return source.Text[source.Fset.Position(node.Pos()).Offset:source.Fset.Position(node.End()).Offset]
}
