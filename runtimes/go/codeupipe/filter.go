package codeupipe

// Filter is the processing unit — takes a Payload in, processes it,
// and returns a (potentially transformed) Payload out.
//
// See also: TypeScript, Python, Rust, C# implementations.
type Filter interface {
	// Call processes a payload and returns the result.
	Call(payload Payload) (Payload, error)
}
