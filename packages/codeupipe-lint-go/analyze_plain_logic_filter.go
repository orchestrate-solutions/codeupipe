package codeupipelint

import (
	"context"
	"fmt"
	"go/ast"
	"go/token"
)

// logicWhat says that a function, a method or a var is not a primitive.
const logicWhat = "has logic and is not a Filter, a Predicate, a Tap, a Hook or a Pipeline"

// AnalyzePlainLogicFilter finds logic that is not in a primitive: CUP-I008, a warning.
//
// Logic is an if, a switch, a type switch, a select, a for (range too), or a
// goto. Logic in a function literal counts for the function around it. && and
// || are not logic.
//
// Flagged, once each: a top-level function (main and init too), a method
// whose receiver type is not a primitive of the file, and the first top-level
// var whose value has logic. Not flagged: a method of a primitive of the file,
// code with no logic, and a _test.go file.
//
// Reads Sources. Writes Findings.
type AnalyzePlainLogicFilter struct{}

func (f AnalyzePlainLogicFilter) Call(ctx context.Context, run *LintRun) error {
	for _, source := range run.Sources {
		if IsTestFile(source.Path) {
			continue
		}
		primitives := map[string]bool{}
		for _, primitive := range PrimitivesIn(source.File) {
			primitives[primitive.Name] = true
		}
		varFlagged := false
		for _, declaration := range source.File.Decls {
			switch declaration := declaration.(type) {
			case *ast.FuncDecl:
				if declaration.Body == nil || !f.hasLogic(declaration.Body) {
					continue
				}
				name := declaration.Name.Name
				if declaration.Recv == nil {
					run.Findings = append(run.Findings, f.finding(source, declaration.Name.Pos(),
						fmt.Sprintf("Function `%s` %s", name, logicWhat)))
					continue
				}
				receiver := ReceiverName(declaration)
				if primitives[receiver] {
					continue
				}
				run.Findings = append(run.Findings, f.finding(source, declaration.Name.Pos(),
					fmt.Sprintf("Method `%s.%s` has logic, and `%s` is not a primitive", receiver, name, receiver)))
			case *ast.GenDecl:
				if declaration.Tok != token.VAR || varFlagged {
					continue
				}
				for _, spec := range declaration.Specs {
					value, ok := spec.(*ast.ValueSpec)
					if !ok || !f.valuesHaveLogic(value.Values) {
						continue
					}
					name := value.Names[0].Name
					run.Findings = append(run.Findings, f.finding(source, value.Names[0].Pos(),
						fmt.Sprintf("Var `%s` %s", name, logicWhat)))
					varFlagged = true
					break
				}
			}
		}
	}
	return nil
}

// hasLogic is true for a node that has an if, a switch, a type switch, a
// select, a for, a range or a goto. It walks into function literals too.
func (AnalyzePlainLogicFilter) hasLogic(node ast.Node) bool {
	found := false
	ast.Inspect(node, func(node ast.Node) bool {
		switch node := node.(type) {
		case *ast.IfStmt, *ast.SwitchStmt, *ast.TypeSwitchStmt, *ast.SelectStmt, *ast.ForStmt, *ast.RangeStmt:
			found = true
		case *ast.BranchStmt:
			if node.Tok == token.GOTO {
				found = true
			}
		}
		return !found
	})
	return found
}

// valuesHaveLogic is true when one of the values has logic.
func (f AnalyzePlainLogicFilter) valuesHaveLogic(values []ast.Expr) bool {
	for _, value := range values {
		if f.hasLogic(value) {
			return true
		}
	}
	return false
}

// finding gives a CUP-I008 finding at pos. what names the function, the method or the var.
func (AnalyzePlainLogicFilter) finding(source Source, pos token.Pos, what string) Finding {
	return MakeFinding(source, pos, LogicOutsidePrimitive, what, 0)
}
