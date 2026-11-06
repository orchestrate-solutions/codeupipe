package codeupipelint

// stepScope is one function, or one function literal: the file, the types
// that it can see, and the names that it binds.
type stepScope struct {
	source    Source
	funcTypes map[string]bool
	// types are the types that are declared in this function, or in a
	// function that encloses it.
	types map[string]bool
	// bindings are the names that the function binds, in source order.
	bindings []stepBinding
}
