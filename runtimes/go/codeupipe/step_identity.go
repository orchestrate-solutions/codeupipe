package codeupipe

import (
	"fmt"
	"reflect"
	"regexp"
	"runtime"
)

// Step identity (conformance/API.md, "Step identity"): a step is identified
// by the fully qualified symbol of the code that runs it, derived with
// reflect (types) and runtime.FuncForPC (functions), e.g.
// "example.com/app/filters.Validate". Both survive stripped release builds.

const anonymousFix = "Declare it at package level (a named type, or a named function for a func adapter " +
	"or Valve predicate) so it has a stable identity and can be tested on its own."

// closureName matches runtime names of func literals and closures:
// "pkg.Outer.func1", "pkg.Outer.func2.3".
var closureName = regexp.MustCompile(`\.func\d+(\.\d+)*$`)

func funcSymbol(fn any, what string) string {
	v := reflect.ValueOf(fn)
	if !v.IsValid() || v.Kind() != reflect.Func || v.IsNil() {
		panic(&AnonymousStep{Message: fmt.Sprintf("%s is not a function. %s", what, anonymousFix)})
	}
	f := runtime.FuncForPC(v.Pointer())
	if f == nil {
		panic(&AnonymousStep{Message: fmt.Sprintf("%s has no symbol. %s", what, anonymousFix)})
	}
	name := f.Name()
	if closureName.MatchString(name) {
		panic(&AnonymousStep{Message: fmt.Sprintf("%s is a func literal or closure (%s). %s", what, name, anonymousFix)})
	}
	return name
}

// identify returns a step's identity, before any #n occurrence number.
func identify(stepValue any, what string) string {
	if v, ok := stepValue.(*Valve); ok {
		return identify(v.inner, "Filter")
	}
	t := reflect.TypeOf(stepValue)
	if t == nil {
		panic(&AnonymousStep{Message: fmt.Sprintf("%s is nil. %s", what, anonymousFix)})
	}
	if t.Kind() == reflect.Func {
		// A func adapter (type F func(Payload) (Payload, error)): the function
		// it wraps is the code that runs, so it is the identity.
		return funcSymbol(stepValue, what)
	}
	for t.Kind() == reflect.Ptr {
		t = t.Elem()
	}
	if t.Name() == "" {
		panic(&AnonymousStep{Message: fmt.Sprintf("%s is an anonymous struct (%s). %s", what, t, anonymousFix)})
	}
	return t.PkgPath() + "." + t.Name()
}

// addSite is the file:line of the code that called an Add method.
func addSite() string {
	// 0 addSite, 1 (*Pipeline).identity, 2 (*Pipeline).AddX, 3 the caller
	if _, file, line, ok := runtime.Caller(3); ok {
		return fmt.Sprintf("%s:%d", file, line)
	}
	return ""
}
