package codeupipelint

import "go/token"

// stepVerdict says what is wrong with a step: the rule, the text of the step
// (or of the name that is followed), what is wrong, and where it is.
type stepVerdict struct {
	rule    string
	subject string
	problem string
	at      token.Pos
}
