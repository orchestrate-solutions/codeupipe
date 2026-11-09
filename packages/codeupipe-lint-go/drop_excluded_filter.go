package codeupipelint

import (
	"context"
	"slices"
)

// DropExcludedFilter drops the files that match a glob of Exclude (CUP config and --exclude).
//
// A glob follows Python's fnmatch, as the Rust linter has it. "*" is any
// text, a "/" too. "?" is one character. "[abc]" is one of the characters,
// "[a-z]" is a range, and "[!a]" is any character but those.
//
// Reads Exclude and Files. Writes Files.
type DropExcludedFilter struct{}

func (f DropExcludedFilter) Call(ctx context.Context, run *LintRun) error {
	excluded := func(file string) bool {
		return slices.ContainsFunc(run.Exclude, func(pattern string) bool {
			return f.glob(file, pattern)
		})
	}
	run.Files = slices.DeleteFunc(run.Files, excluded)
	return nil
}

// glob tells whether path matches pattern.
func (f DropExcludedFilter) glob(path, pattern string) bool {
	return f.matches([]rune(path), []rune(pattern))
}

// matches tells whether path matches pattern, one rune at a time.
func (f DropExcludedFilter) matches(path, pattern []rune) bool {
	if len(pattern) == 0 {
		return len(path) == 0
	}
	switch pattern[0] {
	case '*':
		for skip := 0; skip <= len(path); skip++ {
			if f.matches(path[skip:], pattern[1:]) {
				return true
			}
		}
		return false
	case '?':
		return len(path) > 0 && f.matches(path[1:], pattern[1:])
	case '[':
		return f.matchesClass(path, pattern[1:])
	default:
		return len(path) > 0 && path[0] == pattern[0] && f.matches(path[1:], pattern[1:])
	}
}

// matchesClass tells whether path matches a pattern that starts with a
// bracket. rest is the pattern after the "[". With no "]" the bracket is a
// plain character.
func (f DropExcludedFilter) matchesClass(path, rest []rune) bool {
	if len(path) == 0 {
		return false
	}
	end := slices.Index(rest, ']')
	if end < 0 {
		return path[0] == '[' && f.matches(path[1:], rest)
	}
	class, negated := rest[:end], false
	if len(class) > 0 && class[0] == '!' {
		class, negated = class[1:], true
	}
	return f.inClass(path[0], class) != negated && f.matches(path[1:], rest[end+1:])
}

// inClass tells whether c is one of the characters of class, or in one of its
// ranges such as "a-z".
func (DropExcludedFilter) inClass(c rune, class []rune) bool {
	for at := 0; at < len(class); {
		if at+2 < len(class) && class[at+1] == '-' {
			if class[at] <= c && c <= class[at+2] {
				return true
			}
			at += 3
		} else {
			if class[at] == c {
				return true
			}
			at++
		}
	}
	return false
}
