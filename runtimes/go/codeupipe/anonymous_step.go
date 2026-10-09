package codeupipe

// AnonymousStep is the panic value when a step has no stable identity.
//
// Step identity is a pointer to the filter (conformance/API.md, "Step
// identity"). A func literal or closure, an anonymous struct, or a plain
// *Pipeline nested as a step has none, and is not independently testable,
// so the runtime refuses it when the step is added. (A type declared inside
// a function looks like a package-level type to reflect; the linter catches
// that one.) Like a missing step name before it, this is a mistake in the
// pipeline's blueprint, so it panics rather than returning an error.
type AnonymousStep struct {
	Message string
}

func (e *AnonymousStep) Error() string { return e.Message }
