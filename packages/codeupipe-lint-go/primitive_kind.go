package codeupipelint

import (
	"go/ast"
	"go/token"
	"sort"
	"strings"
)

// PrimitiveKind is a primitive that a type can be. The order is the order
// of precedence: a type with the methods of two kinds is of the first.
type PrimitiveKind int

const (
	PipelineKind PrimitiveKind = iota
	HookKind
	FilterKind
	TapKind
	PredicateKind
)

// Name gives the role word: "Filter", "Pipeline", ...
func (k PrimitiveKind) Name() string {
	return [...]string{"Pipeline", "Hook", "Filter", "Tap", "Predicate"}[k]
}

// Primitive is a type at the top level of a file that is a primitive.
type Primitive struct {
	Name string
	Kind PrimitiveKind
	// Pos is the name in the declaration of the type, or the receiver of
	// its first primitive method when the type is declared in another file.
	Pos token.Pos
}

// The methods that make a type a primitive, with the number of their
// parameters (ctx included) and of their results.
var primitiveMethods = map[string]struct {
	kind            PrimitiveKind
	params, results int
}{
	"AddSteps": {PipelineKind, 1, 0},
	"Before":   {HookKind, 3, 0},
	"After":    {HookKind, 3, 0},
	"OnError":  {HookKind, 4, 0},
	"Call":     {FilterKind, 2, 1},
	"Observe":  {TapKind, 2, 1},
	"Test":     {PredicateKind, 2, 1},
}

// KindOfMethod gives the primitive kind that the method makes its receiver,
// and false for a method that makes no primitive.
func KindOfMethod(method *ast.FuncDecl) (PrimitiveKind, bool) {
	wanted, ok := primitiveMethods[method.Name.Name]
	if !ok || method.Recv == nil {
		return 0, false
	}
	if countFields(method.Type.Params) != wanted.params || countFields(method.Type.Results) != wanted.results {
		return 0, false
	}
	return wanted.kind, true
}

// ReceiverName gives the name of the type of a method's receiver:
// "DiscountFilter" for (f DiscountFilter), (f *DiscountFilter) and
// (f *Wrapper[P]). It is "" for a function.
func ReceiverName(function *ast.FuncDecl) string {
	if function.Recv == nil || len(function.Recv.List) == 0 {
		return ""
	}
	return typeName(function.Recv.List[0].Type)
}

// typeName gives the name of a named type, without a pointer, a package or
// type arguments, and "" for a type with no name.
func typeName(expr ast.Expr) string {
	switch expr := expr.(type) {
	case *ast.Ident:
		return expr.Name
	case *ast.StarExpr:
		return typeName(expr.X)
	case *ast.SelectorExpr:
		return expr.Sel.Name
	case *ast.IndexExpr:
		return typeName(expr.X)
	case *ast.IndexListExpr:
		return typeName(expr.X)
	case *ast.ParenExpr:
		return typeName(expr.X)
	}
	return ""
}

// countFields counts the parameters or results of a list: "a, b int" is two.
func countFields(fields *ast.FieldList) int {
	if fields == nil {
		return 0
	}
	count := 0
	for _, field := range fields.List {
		count += max(len(field.Names), 1)
	}
	return count
}

// embedsHookBase is true for a struct that embeds codeupipe.HookBase or
// HookBaseOf[P].
func embedsHookBase(spec *ast.TypeSpec) bool {
	structType, ok := spec.Type.(*ast.StructType)
	if !ok {
		return false
	}
	for _, field := range structType.Fields.List {
		name := typeName(field.Type)
		if len(field.Names) == 0 && (name == "HookBase" || name == "HookBaseOf") {
			return true
		}
	}
	return false
}

// PrimitivesIn gives the primitives of a file, in the order of the file. A
// type is a primitive when the file has one of its primitive methods
// (AddSteps, Before, After, OnError, Call, Observe, Test, with the shape of
// the interface), or when its struct embeds HookBase.
func PrimitivesIn(file *ast.File) []Primitive {
	declared := map[string]token.Pos{}
	found := map[string]*Primitive{}
	var order []string
	add := func(name string, kind PrimitiveKind, pos token.Pos) {
		if primitive, ok := found[name]; ok {
			primitive.Kind = min(primitive.Kind, kind)
			return
		}
		found[name] = &Primitive{Name: name, Kind: kind, Pos: pos}
		order = append(order, name)
	}
	for _, declaration := range file.Decls {
		switch declaration := declaration.(type) {
		case *ast.GenDecl:
			for _, spec := range declaration.Specs {
				if spec, ok := spec.(*ast.TypeSpec); ok {
					declared[spec.Name.Name] = spec.Name.Pos()
					if embedsHookBase(spec) {
						add(spec.Name.Name, HookKind, spec.Name.Pos())
					}
				}
			}
		case *ast.FuncDecl:
			if kind, ok := KindOfMethod(declaration); ok && ReceiverName(declaration) != "" {
				add(ReceiverName(declaration), kind, declaration.Recv.List[0].Type.Pos())
			}
		}
	}
	primitives := make([]Primitive, 0, len(order))
	for _, name := range order {
		primitive := *found[name]
		if pos, ok := declared[name]; ok {
			primitive.Pos = pos
		}
		primitives = append(primitives, primitive)
	}
	sort.SliceStable(primitives, func(i, j int) bool { return primitives[i].Pos < primitives[j].Pos })
	return primitives
}

// IsTestFile is true for a file that only "go test" builds: name_test.go.
func IsTestFile(path string) bool {
	return strings.HasSuffix(path, "_test.go")
}
