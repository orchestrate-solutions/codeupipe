package codeupipelint

import (
	"go/ast"
	"go/token"
)

// Source is one parsed file.
type Source struct {
	Path string
	Text string
	// Fset gives the line and column of each token.Pos of File.
	Fset *token.FileSet
	// File is the syntax tree, with its comments.
	File *ast.File
	// Markers are the "cup: allow-..." comments of the file.
	Markers []Marker
}

// Marker is a comment line that starts with "cup: allow-...".
type Marker struct {
	Line int
	Col  int
	// Kind is the word after "cup:": "allow-plain", "allow-name", ...
	Kind string
	// Alone is true when the line holds the comment and no code.
	Alone bool
}

// Position gives the line and column of pos, from 1.
func (s Source) Position(pos token.Pos) (int, int) {
	at := s.Fset.Position(pos)
	return at.Line, at.Column
}
