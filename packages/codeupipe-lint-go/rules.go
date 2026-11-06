package codeupipelint

import (
	"fmt"
	"go/token"
)

// The ids of the rules. They are those of the Python, TypeScript and Rust
// linters.
const (
	ParseError            = "CUP-I000"
	FunctionStep          = "CUP-A001"
	LocalTypeStep         = "CUP-A003"
	UnnamedPipeline       = "CUP-A005"
	FunctionPredicate     = "CUP-A008"
	StateRead             = "CUP-I003"
	WriteOutsideFilter    = "CUP-I004"
	OnePrimitivePerFile   = "CUP-I005"
	PrimitiveFileName     = "CUP-I006"
	PrimitiveRoleSuffix   = "CUP-I007"
	LogicOutsidePrimitive = "CUP-I008"
	MarkerAllowsNothing   = "CUP-I009"
)

// Rule is one rule: its id, its short name, what to do about a finding, and
// whether a finding is a warning.
type Rule struct {
	ID      string
	Slug    string
	Fix     string
	Warning bool
}

const namedType = "Declare it at the top level of a file as a named struct type with a method " +
	"(a Valve predicate: a type with Test), so it can be tested on its own."

// Rules are the rules, in the order of their ids. A rule that the Go
// compiler checks (CUP-A002, A009, I001) is not here.
var Rules = []Rule{
	{FunctionStep, "function-step",
		"A step is a named struct type with a method, not a function type. " + namedType, false},
	{LocalTypeStep, "local-type-step", namedType, false},
	{UnnamedPipeline, "unnamed-pipeline-step",
		"A nested pipeline must be a named pipeline (a type with AddSteps, nested as " +
			"codeupipe.NewNamedPipeline(UserOnboardingPipeline{})), named like a filter. " +
			"A plain Pipeline can only run at the top level.", false},
	{FunctionPredicate, "function-predicate",
		"A Valve predicate is a named struct type with Test, not a function type. " + namedType, false},
	{ParseError, "parse-error", "Fix the syntax error so the file can be checked.", false},
	{StateRead, "state-read-in-step",
		"A Filter's result and a Valve's decision must depend only on the Payload. Put what the step " +
			"needs into the Payload, or observe State from a Tap or a Hook.", false},
	{WriteOutsideFilter, "write-outside-filter",
		"Only a Filter writes to the Payload. A Tap, a Predicate and a Hook read it: move the write " +
			"into a Filter.", false},
	{OnePrimitivePerFile, "one-primitive-per-file",
		"Give each Filter, Predicate, Tap, Hook and named Pipeline its own file, so it can be tested " +
			"alone and used again. The pipeline file is where they come together.", false},
	{PrimitiveFileName, "primitive-file-name",
		"The file name of a primitive is its type name in snake_case, so one name gives the other.", false},
	{PrimitiveRoleSuffix, "primitive-role-suffix",
		"A primitive's type name ends with its role (Filter, Tap, Hook, Predicate, Pipeline), so the " +
			"name tells what the type is.", false},
	{LogicOutsidePrimitive, "logic-outside-primitive",
		"Write it as a primitive, so that the pipeline has the logic and it can be tested as a step. " +
			"For logic that must be plain code, say why: // cup: allow-plain <reason>", true},
	{MarkerAllowsNothing, "marker-allows-nothing",
		"Remove it, or put it on the line of the finding that it is for. A comment that allows nothing " +
			"says that the code has an exception that it does not have.", true},
}

// RuleOf gives the rule with the id, and false when there is none.
func RuleOf(id string) (Rule, bool) {
	for _, rule := range Rules {
		if rule.ID == id {
			return rule, true
		}
	}
	return Rule{}, false
}

// MakeFinding gives a finding of the rule id at pos in source. Its message
// reads "<what>. <fix>". callLine is the line of the Add... call around the
// finding, or 0; it is kept only when it is not the line of the finding.
// It panics for an id that is not a rule of this linter.
func MakeFinding(source Source, pos token.Pos, id, what string, callLine int) Finding {
	rule, ok := RuleOf(id)
	if !ok {
		panic(fmt.Sprintf("not a rule of this linter: %s", id))
	}
	line, col := source.Position(pos)
	if callLine == line {
		callLine = 0
	}
	return Finding{
		Path:     source.Path,
		Line:     line,
		Col:      col,
		Rule:     id,
		Slug:     rule.Slug,
		Message:  what + ". " + rule.Fix,
		CallLine: callLine,
		Warning:  rule.Warning,
	}
}
