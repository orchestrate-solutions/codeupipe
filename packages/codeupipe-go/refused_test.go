package codeupipe_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// What the contract refuses with a TypeError when a step is added is a
// compile error in Go. Each shape below is built as a program of its own,
// and the build must fail with the error that names the cause.

const refusedPrelude = `package main

import (
	"context"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

type Order struct{ Price float64 }

func (o *Order) Copy() *Order { copied := *o; return &copied }

type OrderFilter struct{}

func (OrderFilter) Call(context.Context, *Order) error { return nil }

type MarkFilter struct{}

func (MarkFilter) Call(context.Context, *codeupipe.Payload) error { return nil }

type IsOnPredicate struct{}

func (IsOnPredicate) Test(context.Context, *codeupipe.Payload) bool { return true }

func main() {
	ctx := context.Background()
	pipeline := codeupipe.NewPipeline()
	_, _ = ctx, pipeline
`

var refusedShapes = []struct {
	name, code, error string
}{
	{"a function as a step",
		`pipeline.AddFilter(func(context.Context, *codeupipe.Payload) error { return nil })`,
		"does not implement codeupipe.FilterOf[*codeupipe.Payload] (missing method Call)"},
	{"a Tap that is a Filter",
		`pipeline.AddTap(MarkFilter{})`,
		"does not implement codeupipe.TapOf[*codeupipe.Payload] (missing method Observe)"},
	{"the arguments of AddValve in the wrong order",
		`pipeline.AddValve(MarkFilter{}, IsOnPredicate{})`,
		"does not implement codeupipe.PredicateOf[*codeupipe.Payload] (missing method Test)"},
	{"a step for another type",
		`pipeline.AddFilter(OrderFilter{})`,
		"does not implement codeupipe.FilterOf[*codeupipe.Payload] (wrong type for method Call)"},
	{"a run of another type",
		`codeupipe.NewPipelineOf[*Order]().Run(ctx, codeupipe.NewPayload(nil))`,
		"cannot use codeupipe.NewPayload(nil)"},
	{"a type with no Copy of its own type",
		`codeupipe.NewPipelineOf[Order]()`,
		"Order does not satisfy codeupipe.PipelineData[Order]"},
}

func TestWhatTheContractRefusesDoesNotCompile(t *testing.T) {
	if testing.Short() {
		t.Skip("builds one program for each shape")
	}
	tool, err := exec.LookPath("go")
	if err != nil {
		t.Skip("no go command")
	}
	here, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	module := t.TempDir()
	write(t, filepath.Join(module, "go.mod"), "module refused\n\ngo 1.22\n\n"+
		"require github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go v0.0.0\n\n"+
		"replace github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go => "+here+"\n")
	build := func(t *testing.T, name, code string) ([]byte, error) {
		t.Helper()
		dir := filepath.Join(module, name)
		write(t, filepath.Join(dir, "main.go"), refusedPrelude+"\t"+code+"\n}\n")
		command := exec.Command(tool, "build", "-o", os.DevNull, ".")
		command.Dir = dir
		command.Env = append(os.Environ(), "GOFLAGS=-mod=mod", "GOPROXY=off", "GOWORK=off")
		return command.CombinedOutput()
	}
	// The program with the right steps compiles, so a failure below comes
	// from the shape and not from the program around it.
	if out, err := build(t, "allowed", `pipeline.AddValve(IsOnPredicate{}, MarkFilter{})`); err != nil {
		t.Fatalf("the program with the right steps does not compile:\n%s", out)
	}
	for i, shape := range refusedShapes {
		t.Run(shape.name, func(t *testing.T) {
			out, err := build(t, "shape"+string(rune('a'+i)), shape.code)
			if err == nil {
				t.Fatalf("it compiles: %s", shape.code)
			}
			if !strings.Contains(string(out), shape.error) {
				t.Fatalf("the build fails, but not with %q:\n%s", shape.error, out)
			}
		})
	}
}

func write(t *testing.T, path, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}
