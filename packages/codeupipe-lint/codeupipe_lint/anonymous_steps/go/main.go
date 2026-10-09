// Command anonymous_steps finds anonymous pipeline steps in Go source, for
// packages/codeupipe-lint/codeupipe_lint/anonymous_steps/analyze_go.py. Stdlib only: go/parser and go/ast.
//
// Input: file paths, one per line, on stdin. Output: one JSON object per
// finding per line: {"path","line","col","rule","role","what","call_line"}.
//
// A step is an argument of a method named AddFilter, AddTap, AddPipeline,
// AddParallel or AddStreamFilter (any receiver), or of NewValve. Argument
// counts are ignored, so the rule holds with or without step names. It is
// anonymous when it is, or a local name is bound to:
//
//	CUP-A001 a func literal (also converted: FilterFunc(func(...) {...}))
//	CUP-A003 a value of a type declared inside a function (&Local{}, Local{}, new(Local))
//	CUP-A004 an anonymous struct literal (struct{...}{})
//	CUP-A005 a plain pipeline: a NewPipeline() call chain
//
// or the result of calling a package-level function in the same file that
// returns one of those as its first result (a closure factory, including
// `f, err := factory()`). Bindings are resolved per
// function, flattened across blocks; a name bound two different ways is not
// flagged.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/scanner"
	"go/token"
	"os"
	"strings"
)

type finding struct {
	Path     string `json:"path"`
	Line     int    `json:"line"`
	Col      int    `json:"col"`
	Rule     string `json:"rule"`
	Role     string `json:"role"`
	What     string `json:"what"`
	CallLine int    `json:"call_line"`
}

var stepMethods = map[string]string{
	"AddFilter":       "Filter",
	"AddStreamFilter": "Filter",
	"AddTap":          "Tap",
	"AddPipeline":     "Nested pipeline",
	"AddParallel":     "Parallel filter",
}

// class is what an expression is, when anonymous: rule + noun phrase.
type class struct {
	rule string
	noun string
}

var unknown = &class{rule: "?"}

type env struct {
	localTypes map[string]string // type name -> enclosing function
	names      map[string]*class // local name -> class (unknown when opaque)
	parent     *env
}

func (e *env) lookup(name string) *class {
	for s := e; s != nil; s = s.parent {
		if c, ok := s.names[name]; ok {
			if c == unknown {
				return nil
			}
			return c
		}
	}
	return nil
}

func (e *env) localType(name string) (string, bool) {
	for s := e; s != nil; s = s.parent {
		if fn, ok := s.localTypes[name]; ok {
			return fn, true
		}
	}
	return "", false
}

type analyzer struct {
	fset  *token.FileSet
	path  string
	funcs map[string]*ast.FuncDecl
	envs  map[*ast.FuncDecl]*env
	pkg   *env
	out   []finding
	seen  map[string]bool
}

func calleeName(fun ast.Expr) string {
	switch f := fun.(type) {
	case *ast.Ident:
		return f.Name
	case *ast.SelectorExpr:
		return f.Sel.Name
	case *ast.IndexExpr: // generic instantiation
		return calleeName(f.X)
	}
	return ""
}

func unwrap(e ast.Expr) ast.Expr {
	for {
		switch x := e.(type) {
		case *ast.ParenExpr:
			e = x.X
		case *ast.UnaryExpr:
			if x.Op != token.AND {
				return e
			}
			e = x.X
		default:
			return e
		}
	}
}

// isPlainPipeline: NewPipeline() or a method chain rooted at it.
func isPlainPipeline(e ast.Expr) bool {
	e = unwrap(e)
	call, ok := e.(*ast.CallExpr)
	if !ok {
		return false
	}
	if calleeName(call.Fun) == "NewPipeline" {
		return true
	}
	if sel, ok := call.Fun.(*ast.SelectorExpr); ok {
		if _, isCall := unwrap(sel.X).(*ast.CallExpr); isCall {
			return isPlainPipeline(sel.X)
		}
	}
	return false
}

func typeName(t ast.Expr) string {
	switch x := t.(type) {
	case *ast.Ident:
		return x.Name
	case *ast.IndexExpr:
		return typeName(x.X)
	case *ast.IndexListExpr:
		return typeName(x.X)
	}
	return ""
}

func (a *analyzer) classify(expr ast.Expr, e *env, visiting map[*ast.FuncDecl]bool) *class {
	x := unwrap(expr)
	switch v := x.(type) {
	case *ast.FuncLit:
		return &class{"CUP-A001", "a func literal"}
	case *ast.CompositeLit:
		if _, ok := v.Type.(*ast.StructType); ok {
			return &class{"CUP-A004", "an anonymous struct literal"}
		}
		name := typeName(v.Type)
		if fn, ok := e.localType(name); ok && name != "" {
			return &class{"CUP-A003", fmt.Sprintf("a value of %s, a type declared inside %s()", name, fn)}
		}
	case *ast.Ident:
		if c := e.lookup(v.Name); c != nil {
			return &class{c.rule, fmt.Sprintf("`%s`, %s", v.Name, c.noun)}
		}
	case *ast.CallExpr:
		name := calleeName(v.Fun)
		if name == "new" && len(v.Args) == 1 {
			tn := typeName(v.Args[0])
			if fn, ok := e.localType(tn); ok && tn != "" {
				return &class{"CUP-A003", fmt.Sprintf("new(%s), of a type declared inside %s()", tn, fn)}
			}
		}
		if isPlainPipeline(v) {
			return &class{"CUP-A005", "a plain pipeline (NewPipeline())"}
		}
		if len(v.Args) == 1 {
			if _, ok := unwrap(v.Args[0]).(*ast.FuncLit); ok && name != "NewValve" && stepMethods[name] == "" {
				return &class{"CUP-A001", fmt.Sprintf("a func literal converted with %s(...)", name)}
			}
		}
		if id, ok := v.Fun.(*ast.Ident); ok {
			if fd, ok := a.funcs[id.Name]; ok && !visiting[fd] {
				if c := a.returned(fd, visiting); c != nil {
					return &class{c.rule, fmt.Sprintf("the result of %s(), which returns %s", id.Name, c.noun)}
				}
			}
		}
	}
	return nil
}

func (a *analyzer) returned(fd *ast.FuncDecl, visiting map[*ast.FuncDecl]bool) *class {
	if fd.Body == nil {
		return nil
	}
	next := map[*ast.FuncDecl]bool{fd: true}
	for k := range visiting {
		next[k] = true
	}
	e := a.envFor(fd)
	var got *class
	ast.Inspect(fd.Body, func(n ast.Node) bool {
		if got != nil {
			return false
		}
		if _, ok := n.(*ast.FuncLit); ok {
			return false // returns inside a func literal are not this function's
		}
		if r, ok := n.(*ast.ReturnStmt); ok && len(r.Results) >= 1 {
			got = a.classify(r.Results[0], e, next) // f, err: the first result is the step
		}
		return true
	})
	return got
}

func (a *analyzer) bind(e *env, name string, c *class) {
	if name == "_" {
		return
	}
	prev, seen := e.names[name]
	switch {
	case !seen:
		if c == nil {
			c = unknown
		}
		e.names[name] = c
	case prev == unknown || c == nil || prev.rule != c.rule:
		e.names[name] = unknown
	}
}

func (a *analyzer) envFor(fd *ast.FuncDecl) *env {
	if e, ok := a.envs[fd]; ok {
		return e
	}
	e := &env{localTypes: map[string]string{}, names: map[string]*class{}, parent: a.pkg}
	a.envs[fd] = e
	fn := fd.Name.Name
	for _, list := range []*ast.FieldList{fd.Recv, fd.Type.Params, fd.Type.Results} {
		if list == nil {
			continue
		}
		for _, field := range list.List {
			for _, n := range field.Names {
				a.bind(e, n.Name, nil)
			}
		}
	}
	if fd.Body == nil {
		return e
	}
	ast.Inspect(fd.Body, func(n ast.Node) bool {
		if ts, ok := n.(*ast.TypeSpec); ok {
			e.localTypes[ts.Name.Name] = fn
		}
		return true
	})
	a.collectBindings(fd.Body, e)
	return e
}

func (a *analyzer) collectBindings(root ast.Node, e *env) {
	ast.Inspect(root, func(n ast.Node) bool {
		switch s := n.(type) {
		case *ast.AssignStmt:
			for i, lhs := range s.Lhs {
				id, ok := lhs.(*ast.Ident)
				if !ok {
					continue
				}
				var c *class
				if len(s.Lhs) == len(s.Rhs) {
					c = a.classify(s.Rhs[i], e, map[*ast.FuncDecl]bool{})
				} else if i == 0 && len(s.Rhs) == 1 {
					// f, err := factory(): the first result
					c = a.classify(s.Rhs[0], e, map[*ast.FuncDecl]bool{})
				}
				a.bind(e, id.Name, c)
			}
		case *ast.ValueSpec:
			for i, id := range s.Names {
				var c *class
				if len(s.Names) == len(s.Values) {
					c = a.classify(s.Values[i], e, map[*ast.FuncDecl]bool{})
				} else if i == 0 && len(s.Values) == 1 {
					c = a.classify(s.Values[0], e, map[*ast.FuncDecl]bool{})
				}
				a.bind(e, id.Name, c)
			}
		case *ast.RangeStmt:
			for _, k := range []ast.Expr{s.Key, s.Value} {
				if id, ok := k.(*ast.Ident); ok {
					a.bind(e, id.Name, nil)
				}
			}
		case *ast.FuncLit:
			for _, field := range s.Type.Params.List {
				for _, id := range field.Names {
					a.bind(e, id.Name, nil)
				}
			}
		}
		return true
	})
}

func (a *analyzer) report(arg ast.Expr, role string, call *ast.CallExpr, e *env) {
	c := a.classify(arg, e, map[*ast.FuncDecl]bool{})
	if c == nil {
		return
	}
	if c.rule == "CUP-A005" && role == "Valve predicate" {
		return
	}
	pos := a.fset.Position(arg.Pos())
	key := fmt.Sprintf("%d:%d:%s", pos.Line, pos.Column, c.rule)
	if a.seen[key] {
		return
	}
	a.seen[key] = true
	what := "is " + c.noun
	if strings.HasPrefix(c.noun, "`") {
		parts := strings.SplitN(c.noun, ", ", 2)
		what = parts[0] + " is " + parts[1]
	}
	a.out = append(a.out, finding{a.path, pos.Line, pos.Column, c.rule, role, what,
		a.fset.Position(call.Pos()).Line})
}

func (a *analyzer) checkCalls(root ast.Node, e *env) {
	ast.Inspect(root, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if !ok {
			return true
		}
		name := calleeName(call.Fun)
		if role, ok := stepMethods[name]; ok {
			if _, isSel := call.Fun.(*ast.SelectorExpr); isSel {
				for _, arg := range call.Args {
					if lit, ok := unwrap(arg).(*ast.CompositeLit); ok {
						if _, isSlice := lit.Type.(*ast.ArrayType); isSlice {
							for _, el := range lit.Elts {
								a.report(el, role, call, e)
							}
							continue
						}
					}
					a.report(arg, role, call, e)
				}
			}
		} else if name == "NewValve" {
			for i, arg := range call.Args {
				role := "Valve inner filter"
				if i == len(call.Args)-1 {
					role = "Valve predicate"
				}
				a.report(arg, role, call, e)
			}
		}
		return true
	})
}

func analyze(path string) ([]finding, error) {
	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, path, nil, parser.SkipObjectResolution)
	if err != nil {
		line, col := 1, 1
		if list, ok := err.(scanner.ErrorList); ok && len(list) > 0 {
			line, col = list[0].Pos.Line, list[0].Pos.Column
			err = fmt.Errorf("%s", list[0].Msg)
		}
		return []finding{{path, line, col, "CUP-A000", "File", "is not valid Go (" + err.Error() + ")", line}}, nil
	}
	a := &analyzer{fset: fset, path: path, funcs: map[string]*ast.FuncDecl{}, envs: map[*ast.FuncDecl]*env{},
		pkg: &env{localTypes: map[string]string{}, names: map[string]*class{}}, seen: map[string]bool{}}
	for _, d := range file.Decls {
		if fd, ok := d.(*ast.FuncDecl); ok && fd.Recv == nil {
			a.funcs[fd.Name.Name] = fd
		}
	}
	for _, d := range file.Decls {
		if gd, ok := d.(*ast.GenDecl); ok && gd.Tok == token.VAR {
			a.collectBindings(gd, a.pkg)
		}
	}
	for _, d := range file.Decls {
		switch decl := d.(type) {
		case *ast.FuncDecl:
			if decl.Body != nil {
				a.checkCalls(decl.Body, a.envFor(decl))
			}
		case *ast.GenDecl:
			a.checkCalls(decl, a.pkg)
		}
	}
	return a.out, nil
}

func main() {
	enc := json.NewEncoder(os.Stdout)
	in := bufio.NewScanner(os.Stdin)
	in.Buffer(make([]byte, 1024*1024), 1024*1024)
	status := 0
	for in.Scan() {
		path := strings.TrimSpace(in.Text())
		if path == "" {
			continue
		}
		found, err := analyze(path)
		if err != nil {
			fmt.Fprintf(os.Stderr, "%s: %v\n", path, err)
			status = 1
			continue
		}
		for _, f := range found {
			if err := enc.Encode(f); err != nil {
				fmt.Fprintln(os.Stderr, err)
				os.Exit(1)
			}
		}
	}
	os.Exit(status)
}
