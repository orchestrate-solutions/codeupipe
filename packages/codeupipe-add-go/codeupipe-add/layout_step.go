package main

// LayoutStep is one step of a pipeline of a layout: a name, or
// “valve: [Predicate, Filter]“ (ADD.md, "The steps"). Name is empty for a
// valve.
type LayoutStep struct {
	Name      string
	Predicate string
	Filter    string
}
