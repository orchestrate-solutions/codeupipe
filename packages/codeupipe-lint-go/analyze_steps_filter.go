package codeupipelint

import (
	"context"
	"fmt"
	"go/ast"
	"go/token"
	"strings"
)

// The roles of a step: the place of an argument in an Add... call.
const (
	filterRole      = "Filter"
	tapRole         = "Tap"
	pipelineRole    = "Pipeline"
	predicateRole   = "Valve predicate"
	valveFilterRole = "Valve filter"
)

// stepRoles gives the role of each argument of the Add... calls that take a step.
var stepRoles = map[string][]string{
	"AddFilter":   {filterRole},
	"AddTap":      {tapRole},
	"AddPipeline": {pipelineRole},
	"AddValve":    {predicateRole, valveFilterRole},
}

// followDepth limits how many names are followed in a row.
const followDepth = 8

// AnalyzeStepsFilter finds the steps that are not named types: CUP-A001, A003, A005, A008.
//
// A step is the argument of AddFilter, AddTap or AddPipeline, on any
// receiver. The two arguments of AddValve are steps too. A name is followed
// to the value that the same function gave it before the call. A parameter,
// a name from another function, and the result of a call are not followed.
//
// Reads Sources. Writes Findings.
type AnalyzeStepsFilter struct{}

func (f AnalyzeStepsFilter) Call(ctx context.Context, run *LintRun) error {
	for _, source := range run.Sources {
		run.Findings = append(run.Findings, f.findInFile(source)...)
	}
	return nil
}

// findInFile checks each function and each variable declaration of a file.
func (f AnalyzeStepsFilter) findInFile(source Source) []Finding {
	funcTypes := f.funcTypeNames(source.File)
	var findings []Finding
	for _, decl := range source.File.Decls {
		switch decl := decl.(type) {
		case *ast.FuncDecl:
			if decl.Body != nil {
				params := f.paramBindings(decl.Type, decl.Recv)
				findings = append(findings, f.findInBody(source, funcTypes, nil, decl.Body, params)...)
			}
		case *ast.GenDecl:
			findings = append(findings, f.findInBody(source, funcTypes, nil, decl, nil)...)
		}
	}
	return findings
}

// findInBody checks the Add... calls in root, a function body or a
// declaration. It checks each function literal in root in the same way, and
// the local types of root are visible in it. outer are the local types of
// the function that encloses root.
func (f AnalyzeStepsFilter) findInBody(source Source, funcTypes, outer map[string]bool, root ast.Node, params []stepBinding) []Finding {
	scope := &stepScope{source: source, funcTypes: funcTypes, types: map[string]bool{}, bindings: params}
	for name := range outer {
		scope.types[name] = true
	}
	_, isDecl := root.(*ast.GenDecl)
	var calls []*ast.CallExpr
	var lits []*ast.FuncLit
	ast.Inspect(root, func(node ast.Node) bool {
		switch node := node.(type) {
		case *ast.FuncLit:
			// A function literal is a function of its own.
			lits = append(lits, node)
			return false
		case *ast.TypeSpec:
			if !isDecl {
				scope.types[node.Name.Name] = true
			}
		case *ast.ValueSpec:
			f.bindSpec(scope, node)
		case *ast.AssignStmt:
			f.bindAssign(scope, node)
		case *ast.RangeStmt:
			f.bindRange(scope, node)
		case *ast.CallExpr:
			if f.isStepCall(node) {
				calls = append(calls, node)
			}
		}
		return true
	})

	var findings []Finding
	for _, call := range calls {
		findings = append(findings, f.findInCall(scope, call)...)
	}
	for _, lit := range lits {
		litParams := f.paramBindings(lit.Type, nil)
		findings = append(findings, f.findInBody(source, funcTypes, scope.types, lit.Body, litParams)...)
	}
	return findings
}

// findInCall gives a finding for each step of one Add... call that is wrong.
func (f AnalyzeStepsFilter) findInCall(scope *stepScope, call *ast.CallExpr) []Finding {
	sel := call.Fun.(*ast.SelectorExpr)
	callLine, _ := scope.source.Position(sel.Sel.Pos())
	var findings []Finding
	for index, role := range stepRoles[sel.Sel.Name] {
		if index >= len(call.Args) {
			break
		}
		verdict := f.classify(call.Args[index], role, scope, call.Pos(), 0)
		if verdict == nil {
			continue
		}
		noun := "Step"
		if role == predicateRole {
			noun = "Predicate"
		}
		what := fmt.Sprintf("%s `%s` %s", noun, verdict.subject, verdict.problem)
		findings = append(findings, MakeFinding(scope.source, verdict.at, verdict.rule, what, callLine))
	}
	return findings
}

// classify says what is wrong with expr as a step of role, if anything. A
// name is looked up at pos.
func (f AnalyzeStepsFilter) classify(expr ast.Expr, role string, scope *stepScope, pos token.Pos, depth int) *stepVerdict {
	if depth > followDepth {
		return nil
	}
	expr = f.unwrap(expr)
	switch expr := expr.(type) {
	case *ast.Ident:
		value, from, ok := f.lookup(scope, expr.Name, pos)
		if !ok || value == nil {
			return nil
		}
		verdict := f.classify(value, role, scope, from, depth+1)
		if verdict == nil {
			return nil
		}
		verdict.subject = expr.Name
		verdict.at = expr.Pos()
		return verdict
	case *ast.CompositeLit:
		return f.classifyLiteral(scope, expr)
	case *ast.CallExpr:
		return f.classifyCall(scope, expr, role)
	}
	return nil
}

// classifyLiteral finds a composite literal of a local type, or of an
// anonymous struct type: CUP-A003.
func (f AnalyzeStepsFilter) classifyLiteral(scope *stepScope, lit *ast.CompositeLit) *stepVerdict {
	switch typ := lit.Type.(type) {
	case *ast.Ident:
		if scope.types[typ.Name] {
			return &stepVerdict{rule: LocalTypeStep, subject: f.textOf(scope.source, lit),
				problem: "is of a type that is declared in a function", at: lit.Pos()}
		}
	case *ast.StructType:
		return &stepVerdict{rule: LocalTypeStep, subject: f.textOf(scope.source, lit),
			problem: "is of an anonymous struct type", at: lit.Pos()}
	}
	return nil
}

// classifyCall finds a conversion to a function type (CUP-A001, A008), and a
// plain Pipeline as a step (CUP-A005).
func (f AnalyzeStepsFilter) classifyCall(scope *stepScope, call *ast.CallExpr, role string) *stepVerdict {
	if ident, ok := f.unwrap(call.Fun).(*ast.Ident); ok && scope.funcTypes[ident.Name] {
		rule := FunctionStep
		if role == predicateRole {
			rule = FunctionPredicate
		}
		return &stepVerdict{rule: rule, subject: f.textOf(scope.source, call),
			problem: "is a function type", at: call.Pos()}
	}
	name := f.calleeName(call.Fun)
	if (name == "NewPipeline" || name == "NewPipelineOf") && role == pipelineRole {
		return &stepVerdict{rule: UnnamedPipeline, subject: f.textOf(scope.source, call),
			problem: "is a plain Pipeline, nested as a step", at: call.Pos()}
	}
	return nil
}

// isStepCall tells whether call is an Add... call that takes a step.
func (f AnalyzeStepsFilter) isStepCall(call *ast.CallExpr) bool {
	sel, ok := call.Fun.(*ast.SelectorExpr)
	if !ok {
		return false
	}
	_, found := stepRoles[sel.Sel.Name]
	return found
}

// funcTypeNames gives the names of the types that the file declares as a
// function type, at the top level or in a function.
func (f AnalyzeStepsFilter) funcTypeNames(file *ast.File) map[string]bool {
	names := map[string]bool{}
	ast.Inspect(file, func(node ast.Node) bool {
		if spec, ok := node.(*ast.TypeSpec); ok {
			if _, isFunc := spec.Type.(*ast.FuncType); isFunc {
				names[spec.Name.Name] = true
			}
		}
		return true
	})
	return names
}

// unwrap gives expr without its parentheses and its "&".
func (f AnalyzeStepsFilter) unwrap(expr ast.Expr) ast.Expr {
	for {
		switch inner := expr.(type) {
		case *ast.ParenExpr:
			expr = inner.X
		case *ast.UnaryExpr:
			if inner.Op != token.AND {
				return expr
			}
			expr = inner.X
		default:
			return expr
		}
	}
}

// textOf gives the text of node, with each run of white space made to one space.
func (f AnalyzeStepsFilter) textOf(source Source, node ast.Node) string {
	start := source.Fset.Position(node.Pos()).Offset
	end := source.Fset.Position(node.End()).Offset
	return strings.Join(strings.Fields(source.Text[start:end]), " ")
}

// calleeName gives the name of a called function: "NewPipeline" for
// "codeupipe.NewPipeline()" and for "NewPipeline[T]()".
func (f AnalyzeStepsFilter) calleeName(fun ast.Expr) string {
	switch fun := fun.(type) {
	case *ast.Ident:
		return fun.Name
	case *ast.SelectorExpr:
		return fun.Sel.Name
	case *ast.IndexExpr:
		return f.calleeName(fun.X)
	case *ast.ParenExpr:
		return f.calleeName(fun.X)
	}
	return ""
}

// lookup gives the value that name was given before pos, and the position
// where that value was given. ok is false when no binding of name is in
// effect at pos.
func (f AnalyzeStepsFilter) lookup(scope *stepScope, name string, pos token.Pos) (value ast.Expr, from token.Pos, ok bool) {
	for index := len(scope.bindings) - 1; index >= 0; index-- {
		binding := scope.bindings[index]
		if binding.name != name || binding.from >= pos {
			continue
		}
		if binding.until != 0 && pos >= binding.until {
			continue
		}
		return binding.value, binding.from, true
	}
	return nil, 0, false
}

// bindAssign records the names of an assignment, "x := V" or "x = V".
func (f AnalyzeStepsFilter) bindAssign(scope *stepScope, stmt *ast.AssignStmt) {
	if stmt.Tok != token.DEFINE && stmt.Tok != token.ASSIGN {
		return
	}
	for index, lhs := range stmt.Lhs {
		ident, ok := lhs.(*ast.Ident)
		if !ok || ident.Name == "_" {
			continue
		}
		var value ast.Expr
		if len(stmt.Lhs) == len(stmt.Rhs) {
			value = stmt.Rhs[index]
		}
		scope.bindings = append(scope.bindings, stepBinding{name: ident.Name, from: stmt.End(), value: value})
	}
}

// bindSpec records the names of a var declaration, "var x = V".
func (f AnalyzeStepsFilter) bindSpec(scope *stepScope, spec *ast.ValueSpec) {
	for index, name := range spec.Names {
		if name.Name == "_" {
			continue
		}
		var value ast.Expr
		if len(spec.Values) == len(spec.Names) {
			value = spec.Values[index]
		}
		scope.bindings = append(scope.bindings, stepBinding{name: name.Name, from: spec.End(), value: value})
	}
}

// bindRange records the names of a range loop. They have no value to follow,
// and they hide the names before them, in the loop.
func (f AnalyzeStepsFilter) bindRange(scope *stepScope, loop *ast.RangeStmt) {
	for _, expr := range []ast.Expr{loop.Key, loop.Value} {
		ident, ok := expr.(*ast.Ident)
		if !ok || ident.Name == "_" {
			continue
		}
		binding := stepBinding{name: ident.Name, from: loop.Pos()}
		if loop.Tok == token.DEFINE {
			binding.until = loop.End()
		}
		scope.bindings = append(scope.bindings, binding)
	}
}

// paramBindings gives the parameters, the receiver and the results of a
// function. They have no value to follow.
func (f AnalyzeStepsFilter) paramBindings(funcType *ast.FuncType, recv *ast.FieldList) []stepBinding {
	var bindings []stepBinding
	for _, list := range []*ast.FieldList{recv, funcType.Params, funcType.Results} {
		if list == nil {
			continue
		}
		for _, field := range list.List {
			for _, name := range field.Names {
				if name.Name != "_" {
					bindings = append(bindings, stepBinding{name: name.Name})
				}
			}
		}
	}
	return bindings
}
