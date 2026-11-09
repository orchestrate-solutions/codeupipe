package codeupipelint

import (
	"go/ast"
	"go/token"
)

// stepBinding is a name that a function gives a value. It is in effect from
// the position from, up to the position until, or to the end of the
// function when until is 0. A nil value is a name that is not followed.
type stepBinding struct {
	name  string
	from  token.Pos
	until token.Pos
	value ast.Expr
}
