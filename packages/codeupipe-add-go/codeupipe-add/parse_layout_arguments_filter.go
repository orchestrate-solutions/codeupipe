package main

import (
	"context"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// ParseLayoutArgumentsFilter reads the arguments of
//
//	codeupipe add --layout FILE
//
// Filter (sync).
//
// Input keys: “args“ (the arguments after add).
// Output keys: “layout_path“. A kind, a name, a dir or --description with
// --layout is refused with exit code 2: they are in the layout.
type ParseLayoutArgumentsFilter struct{}

// Call finds the file after --layout (or in --layout=FILE).
func (ParseLayoutArgumentsFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	args, _ := payload.Get("args").([]string)
	path, others := "", 0
	for i := 0; i < len(args); i++ {
		switch {
		case args[i] == "--layout" && i+1 < len(args):
			path = args[i+1]
			i++
		case args[i] == "--layout":
			return &Refusal{ExitCode: 2, Message: "--layout needs a file after it."}
		case strings.HasPrefix(args[i], "--layout="):
			path = strings.TrimPrefix(args[i], "--layout=")
		default:
			others++
		}
	}
	if others > 0 {
		return &Refusal{ExitCode: 2, Message: "--layout takes no kind, name, dir or --description: they are in the layout."}
	}
	payload.Insert("layout_path", path)
	return nil
}

// usesLayout says that the arguments ask for a layout, so main runs Layout
// and not Add.
func usesLayout(args []string) bool {
	for _, arg := range args {
		if arg == "--layout" || strings.HasPrefix(arg, "--layout=") {
			return true
		}
	}
	return false
}
