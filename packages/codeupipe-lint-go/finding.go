package codeupipelint

import "fmt"

// Finding is one finding, at Path:Line:Col (line and column start at 1).
type Finding struct {
	Path    string
	Line    int
	Col     int
	Rule    string
	Slug    string
	Message string
	// CallLine is the line of the Add... call around the finding, when it is
	// a different line: a comment that suppresses can be on that line too.
	// It is 0 when there is no such line.
	CallLine int
	// Warning is reported and does not fail the run, unless the run is
	// strict.
	Warning bool
}

// Format gives "path:line:col  RULE slug  message", with "warning: " before
// the message of a warning.
// cup: allow-plain the text of one finding, for the report
func (f Finding) Format() string {
	warning := ""
	if f.Warning {
		warning = "warning: "
	}
	return fmt.Sprintf("%s:%d:%d  %s %s  %s%s", f.Path, f.Line, f.Col, f.Rule, f.Slug, warning, f.Message)
}
