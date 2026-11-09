package main

import (
	"fmt"
	"os"
	"path/filepath"
)

// Refusal says the command cannot do what it was asked, and writes nothing.
//
// ExitCode is 1 when a file exists, and 2 when the arguments cannot be used
// (ADD.md, "What the command prints, and its exit code"). Message names what
// cannot be used; main prints it on stderr.
type Refusal struct {
	ExitCode int
	Message  string
}

func (r *Refusal) Error() string {
	return fmt.Sprintf("refused with exit %d: %s", r.ExitCode, r.Message)
}

// goMod gives the module of the project, from its go.mod, and the error of
// reading that file. A project with no go.mod has no module and no error.
func goMod(root string) (string, error) {
	text, err := os.ReadFile(filepath.Join(root, "go.mod"))
	if os.IsNotExist(err) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	return moduleOfGoMod(string(text)), nil
}
