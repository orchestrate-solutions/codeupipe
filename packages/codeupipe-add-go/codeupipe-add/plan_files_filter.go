package main

import (
	"context"
	"os"
	"path/filepath"
	"strings"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// PlanFilesFilter says where the two files go, and what package they are in.
//
// Go keeps a test beside its source (ADD.md, "The files"), so both files are
// in <dir>, and the package of the new files is the package of the other .go
// files in <dir>, or else the name of the directory in small letters, with
// each character that a Go name cannot have removed (ADD.md, "Rust and Go:
// the package").
//
// Filter (sync).
//
// Input keys: “root“, “directory“ and “snake“.
// Output keys: “component_path“ and “test_path“ (relative to the root,
// with /), “component_dir“ and “package_name“. A directory that cannot be
// read is refused with exit code 2.
type PlanFilesFilter struct{}

// Call plans the two paths and the package name.
func (PlanFilesFilter) Call(ctx context.Context, payload *codeupipe.Payload) error {
	root, _ := payload.Get("root").(string)
	directory, _ := payload.Get("directory").(string)
	snake, _ := payload.Get("snake").(string)
	name, err := packageName(root, directory)
	if err != nil {
		return &Refusal{ExitCode: 2, Message: "Cannot read the directory of the component: " + err.Error()}
	}
	component, test, dir := pathsFor(directory, snake)
	payload.Insert("component_path", component).
		Insert("test_path", test).
		Insert("component_dir", dir).
		Insert("package_name", name)
	return nil
}

// packageName gives the package of a directory: the package of its first .go
// componentFile_ that has one, or the name of the directory. An empty directory, and
// “.“, give the name of the directory: for “.“ that is the name of the
// project, which is what a project with no other .go componentFile_ has.
func packageName(root, directory string) (string, error) {
	dir := filepath.Join(root, directory)
	entries, err := os.ReadDir(dir)
	if os.IsNotExist(err) {
		// A new directory: its name is the package, and the step that
		// writes makes it.
		return directoryName(directory, root), nil
	}
	if err != nil {
		return "", err
	}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".go") {
			continue
		}
		if name, found := packageOfFile(filepath.Join(dir, entry.Name())); found {
			return name, nil
		}
	}
	return directoryName(directory, root), nil
}

// packageOfFile gives the package clause of a .go file. A file that cannot be
func packageOfFile(path string) (string, bool) {
	text, err := os.ReadFile(path)
	if err != nil {
		return "", false
	}
	return packageClause(string(text))
}

// packageClause finds “package name“ at the start of a line of the text of
// a componentFile_, before any code. The scan stops at the first line that is not an
// empty line, a comment or a build tag, so a “package“ word in a comment
// below the code does not give a package.
func packageClause(text string) (string, bool) {
	for _, line := range strings.Split(text, "\n") {
		fields := strings.Fields(strings.TrimSuffix(line, "\r"))
		if len(fields) == 0 {
			continue
		}
		if len(fields) == 2 && fields[0] == "package" && validPackageName(fields[1]) {
			return fields[1], true
		}
		if strings.HasPrefix(line, "//") || strings.HasPrefix(line, "/*") || strings.HasPrefix(line, "*") {
			continue
		}
		return "", false
	}
	return "", false
}

// directoryName gives the name of the directory as a Go package name: its
// last part in small letters, with each character that a Go name cannot have
// removed. For “.“ it is the name of the project directory.
func directoryName(directory, root string) string {
	if directory == "" || directory == "." {
		base := filepath.Base(root)
		if name := goName(base); name != "" {
			return name
		}
		return "main"
	}
	parts := strings.Split(filepath.ToSlash(directory), "/")
	for i := len(parts) - 1; i >= 0; i-- {
		if parts[i] != "" && parts[i] != "." && parts[i] != ".." {
			if name := goName(parts[i]); name != "" {
				return name
			}
			return "main"
		}
	}
	return "main"
}

// goName keeps letters and digits, in small letters, and drops the rest.
func goName(s string) string {
	var out strings.Builder
	for _, r := range strings.ToLower(s) {
		if r >= 'a' && r <= 'z' || r >= '0' && r <= '9' {
			out.WriteRune(r)
		}
	}
	return out.String()
}

func validPackageName(s string) bool {
	if s == "" || reserved[s] {
		return false
	}
	for i, r := range s {
		if !(r == '_' || r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || i > 0 && r >= '0' && r <= '9') {
			return false
		}
	}
	return true
}

// reserved are the words that a package clause cannot have.
var reserved = map[string]bool{"init": true}

// pathsFor gives the two paths of the component in directory: the component
// file and its test, beside it, each relative to the root with /.
func pathsFor(directory, snake string) (component, test, dir string) {
	parts := []string{}
	for _, part := range strings.Split(filepath.ToSlash(directory), "/") {
		if part != "" && part != "." {
			parts = append(parts, part)
		}
	}
	parts = append(parts, snake)
	here := strings.Join(parts, "/")
	return here + ".go", here + "_test.go", strings.Join(parts[:len(parts)-1], "/")
}
