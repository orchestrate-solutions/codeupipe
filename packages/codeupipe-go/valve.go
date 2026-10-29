package codeupipe

// valve joins a Predicate to a Filter: the Filter runs only when the
// Predicate is true. Pipeline.AddValve makes one. It is not a public name.
type valve[P any] struct {
	predicate PredicateOf[P]
	filter    FilterOf[P]
}
