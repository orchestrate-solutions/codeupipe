package main

import (
	"context"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// ParseArgumentsFilter reads the arguments that come after “add“:
//
//	codeupipe add <kind> <name> [dir] [--description TEXT]
//
// Filter (sync).
//
// Input keys: “args“ (the arguments after add).
// Output keys: “kind“, “name“, “directory“ (“.“ with none) and
// “description“ (“""“ with none). An argument that cannot be used is
// refused with exit code 2.
type ParseArgumentsFilter struct{}

// Call reads the arguments in order: kind, name, dir, and then
// --description, which can come before or after the dir.
func (ParseArgumentsFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	args, _ := payload.Get("args").([]string)
	rest := []string{}
	description := ""
	for i := 0; i < len(args); i++ {
		if args[i] == "--description" {
			if i+1 == len(args) {
				return &Refusal{ExitCode: 2, Message: "--description needs a text after it."}
			}
			description = args[i+1]
			i++
			continue
		}
		rest = append(rest, args[i])
	}
	if len(rest) == 0 {
		return &Refusal{ExitCode: 2, Message: "codeupipe add needs a kind: filter, predicate, tap, hook or pipeline."}
	}
	if len(rest) == 1 {
		return &Refusal{ExitCode: 2, Message: "codeupipe add needs a name for the " + rest[0] + "."}
	}
	if len(rest) > 3 {
		return &Refusal{ExitCode: 2, Message: "Too many arguments: " + strings.Join(rest, " ")}
	}
	directory := "."
	if len(rest) == 3 {
		directory = rest[2]
	}
	payload.Insert("kind", rest[0]).Insert("name", rest[1]).
		Insert("directory", directory).Insert("description", description)
	return nil
}
