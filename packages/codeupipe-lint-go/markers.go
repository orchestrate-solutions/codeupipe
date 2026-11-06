package codeupipelint

import (
	"go/ast"
	"go/token"
	"strings"
	"unicode"
)

// MarkersOf gives each line of a comment of file that starts with
// "cup: allow-...". Text in a string is not a comment, so it is not a
// marker. A doc comment is a comment, so a marker can be its last line.
func MarkersOf(fset *token.FileSet, file *ast.File, text string) []Marker {
	lines := strings.Split(text, "\n")
	var markers []Marker
	for _, group := range file.Comments {
		for _, comment := range group.List {
			start := fset.Position(comment.Slash)
			for index, piece := range strings.Split(comment.Text, "\n") {
				kind := markerKind(stripCommentLead(piece))
				if kind == "" {
					continue
				}
				line := start.Line + index
				lead := len(piece) - len(strings.TrimLeft(stripCommentLead(piece), " \t"))
				col := lead + 1
				if index == 0 {
					col = start.Column + lead
				}
				// The first line of the comment may have code before it.
				alone := index > 0 || strings.TrimSpace(lines[line-1][:start.Column-1]) == ""
				markers = append(markers, Marker{Line: line, Col: col, Kind: kind, Alone: alone})
			}
		}
	}
	return markers
}

// stripCommentLead gives piece without the space and the comment characters
// at its start: "//", "/*", or the "*" of a line inside a block comment.
func stripCommentLead(piece string) string {
	piece = strings.TrimLeft(piece, " \t")
	switch {
	case strings.HasPrefix(piece, "//"):
		piece = piece[2:]
	case strings.HasPrefix(piece, "/*"):
		piece = strings.TrimLeft(piece[2:], "*")
	case strings.HasPrefix(piece, "*") && !strings.HasPrefix(piece, "*/"):
		piece = piece[1:]
	}
	return strings.TrimLeft(piece, " \t")
}

// markerKind gives "allow-plain" for "cup: allow-plain the reason", and ""
// for text that is not a marker.
func markerKind(text string) string {
	rest, ok := strings.CutPrefix(text, "cup:")
	if !ok {
		return ""
	}
	rest = strings.TrimLeft(rest, " \t")
	if !strings.HasPrefix(rest, "allow-") {
		return ""
	}
	end := strings.IndexFunc(rest, func(r rune) bool {
		return !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-')
	})
	if end < 0 {
		return rest
	}
	return rest[:end]
}
