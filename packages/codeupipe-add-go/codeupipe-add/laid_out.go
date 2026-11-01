package main

// LaidOut is one component of a layout: what the file says, and what each
// step of the Layout pipeline adds.
type LaidOut struct {
	// Kind, Name and Description are those of the file.
	Kind        string
	Name        string
	Description string
	// Steps and Hooks are only for a pipeline.
	Steps []LayoutStep
	Hooks []string
	// TypeName, Snake, ComponentPath, TestPath and PackageName are those of
	// phase 1 (NameComponentsFilter).
	TypeName      string
	Snake         string
	ComponentPath string
	TestPath      string
	PackageName   string
	// Calls are the steps of a pipeline, then its hooks (ResolveStepsFilter).
	Calls []LayoutCall
	// ComponentText and TestText are the text of the two files
	// (RenderLayoutFilter).
	ComponentText string
	TestText      string
}
