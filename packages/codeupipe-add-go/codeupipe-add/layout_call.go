package main

// LayoutCall is one call of a pipeline of a layout: the method of the
// pipeline (“AddFilter“) and the type names in it, in order.
type LayoutCall struct {
	Method string
	Types  []string
}
