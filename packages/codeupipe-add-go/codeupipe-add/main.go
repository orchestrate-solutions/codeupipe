// cup-add is the entry of "codeupipe add" for Go (conformance/ADD.md).
//
//	codeupipe add <kind> <name> [dir] [--description TEXT]
//	codeupipe add --layout cup.layout.yaml
//
// It runs in the root of the project, makes the component file and its test
// (of each component of a layout), prints each file that it made, one path
// in each line, component first, and gives the exit code: 0 the files are
// made, 1 a file exists (nothing is written), 2 the arguments cannot be used
// (nothing is written). With --layout, a file that exists is kept, and the
// exit code is 0.
//
// cup: allow-plain the edge of the program: it reads the arguments, runs the
// pipeline, prints what happened, and gives the exit code
package main

import (
	"context"
	"errors"
	"fmt"
	"os"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

func main() {
	root, err := os.Getwd()
	if err != nil {
		fmt.Fprintln(os.Stderr, "Cannot read the directory of the project:", err)
		os.Exit(2)
	}
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr, root))
}

// run is the command for the tests and for main: the arguments in, the two
// files out, and the exit code.
func run(args []string, stdout, stderr *os.File, root string) int {
	if usesLayout(args) {
		return runLayout(args, stdout, stderr, root)
	}
	module, moduleErr := goMod(root)
	out, refusal := runPipeline(codeupipe.NewPayload(map[string]any{
		"root": root, "args": args, "module": module, "module_error": moduleErr}))
	if refusal != nil {
		fmt.Fprintln(stderr, refusal.Message)
		return refusal.ExitCode
	}
	for _, path := range written(out) {
		fmt.Fprintln(stdout, path)
	}
	return 0
}

// runLayout is the command with --layout: each kept file on stderr, with the
// pipelines whose steps changed, then each file that it wrote on stdout.
func runLayout(args []string, stdout, stderr *os.File, root string) int {
	out, err := codeupipe.NewNamedPipeline(Layout{}).Run(context.Background(),
		codeupipe.NewPayload(map[string]any{"root": root, "args": args}))
	if err != nil {
		var refusal *Refusal
		if !errors.As(err, &refusal) {
			refusal = &Refusal{ExitCode: 2, Message: err.Error()}
		}
		fmt.Fprintln(stderr, refusal.Message)
		return refusal.ExitCode
	}
	kept, _ := out.Get("kept").([]string)
	stale, _ := out.Get("stale").([]string)
	for _, path := range kept {
		if contains(stale, path) {
			fmt.Fprintln(stderr, path+" exists, kept, and its steps are not those of the layout. "+
				"Change the file: the command does not write it again.")
		} else {
			fmt.Fprintln(stderr, path+" exists, kept")
		}
	}
	for _, path := range written(out) {
		fmt.Fprintln(stdout, path)
	}
	return 0
}

// runPipeline runs the six steps of the command, and gives the Refusal that
// stopped the run, if any.
func runPipeline(in *codeupipe.Payload) (*codeupipe.Payload, *Refusal) {
	out, err := codeupipe.NewNamedPipeline(Add{}).Run(context.Background(), in)
	if err != nil {
		var refusal *Refusal
		if errors.As(err, &refusal) {
			return nil, refusal
		}
		return nil, &Refusal{ExitCode: 2, Message: err.Error()}
	}
	return out, nil
}

// written gives the paths that the run made, component first.
func written(out *codeupipe.Payload) []string {
	list, _ := out.Get("written").([]string)
	return list
}
