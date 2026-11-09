package codeupipelint

import (
	"context"
	"fmt"
	"go/ast"
	"go/token"
)

// AnalyzeStateReadsFilter finds a Filter or a Predicate that reads the State of a pipeline: CUP-I003.
//
// In the body of a Filter's Call or a Predicate's Test, it flags each call
// E.State() with no arguments, on any E, and each field of the receiver
// whose type is State (with any package name). The struct of the receiver
// must be declared in the same file. A Tap and a Hook are not checked.
//
// Reads Sources. Writes Findings.
type AnalyzeStateReadsFilter struct{}

func (f AnalyzeStateReadsFilter) Call(ctx context.Context, run *LintRun) error {
	for _, source := range run.Sources {
		held := f.stateFields(source.File)
		for _, declaration := range source.File.Decls {
			function, ok := declaration.(*ast.FuncDecl)
			if !ok || function.Recv == nil || function.Body == nil {
				continue
			}
			kind, ok := KindOfMethod(function)
			if !ok || (kind != FilterKind && kind != PredicateKind) {
				continue
			}
			run.Findings = append(run.Findings, f.reads(source, function, kind, held)...)
		}
	}
	return nil
}

// stateFields gives, for each struct of the file, the names of its fields
// whose type is State.
func (AnalyzeStateReadsFilter) stateFields(file *ast.File) map[string]map[string]bool {
	held := map[string]map[string]bool{}
	for _, declaration := range file.Decls {
		general, ok := declaration.(*ast.GenDecl)
		if !ok {
			continue
		}
		for _, spec := range general.Specs {
			typeSpec, ok := spec.(*ast.TypeSpec)
			if !ok {
				continue
			}
			structType, ok := typeSpec.Type.(*ast.StructType)
			if !ok {
				continue
			}
			fields := map[string]bool{}
			for _, field := range structType.Fields.List {
				if typeName(field.Type) != "State" {
					continue
				}
				for _, name := range field.Names {
					fields[name.Name] = true
				}
			}
			held[typeSpec.Name.Name] = fields
		}
	}
	return held
}

// reads gives the State reads in the body of one step method.
func (f AnalyzeStateReadsFilter) reads(source Source, function *ast.FuncDecl, kind PrimitiveKind, held map[string]map[string]bool) []Finding {
	receiver := ReceiverName(function)
	variable := f.receiverVariable(function)
	fields := held[receiver]
	var found []Finding
	seen := map[token.Pos]bool{}
	flag := func(node ast.Node) {
		if seen[node.Pos()] {
			return
		}
		seen[node.Pos()] = true
		what := fmt.Sprintf("%s `%s` reads the State of a pipeline in `%s`: `%s`",
			kind.Name(), receiver, function.Name.Name, f.text(source, node))
		found = append(found, MakeFinding(source, node.Pos(), StateRead, what, 0))
	}
	ast.Inspect(function.Body, func(node ast.Node) bool {
		switch node := node.(type) {
		case *ast.CallExpr:
			selector, ok := node.Fun.(*ast.SelectorExpr)
			if ok && selector.Sel.Name == "State" && len(node.Args) == 0 {
				flag(node)
			}
		case *ast.SelectorExpr:
			base, ok := node.X.(*ast.Ident)
			if ok && variable != "" && base.Name == variable && fields[node.Sel.Name] {
				flag(node)
			}
		}
		return true
	})
	return found
}

// receiverVariable gives the name of the receiver's variable, such as "f"
// in (f CountFilter). It is "" when the receiver has no name.
func (AnalyzeStateReadsFilter) receiverVariable(function *ast.FuncDecl) string {
	if len(function.Recv.List) == 0 || len(function.Recv.List[0].Names) == 0 {
		return ""
	}
	return function.Recv.List[0].Names[0].Name
}

// text gives the source code of a node.
func (AnalyzeStateReadsFilter) text(source Source, node ast.Node) string {
	return source.Text[source.Fset.Position(node.Pos()).Offset:source.Fset.Position(node.End()).Offset]
}
