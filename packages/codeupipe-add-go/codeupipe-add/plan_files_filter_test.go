package main

import (
	"path/filepath"
	"testing"
)

// planned gives what PlanFilesFilter makes in a project: the two paths, the
// directory of the component and its package name.
func planned(t *testing.T, files map[string]string, directory, snake string) (component, test, dir, pkg string, code int, stderr string) {
	t.Helper()
	return plannedIn(t, t.TempDir(), files, directory, snake)
}

// plannedIn is planned for a project root that the test made itself.
func plannedIn(t *testing.T, root string, files map[string]string, directory, snake string) (component, test, dir, pkg string, code int, stderr string) {
	t.Helper()
	for path, body := range files {
		write(t, filepath.Join(root, path), body)
	}
	out, refusal := runStep(PlanFilesFilter{}, newInput(root, directory, snake))
	if refusal != nil {
		return "", "", "", "", refusal.ExitCode, refusal.Message
	}
	return text(out, "component_path"), text(out, "test_path"), text(out, "component_dir"),
		text(out, "package_name"), 0, ""
}

func TestTheTestFileIsBesideTheComponent(t *testing.T) {
	component, test, dir, _, code, _ := planned(t, nil, ".", "discount_filter")
	same(t, code, 0)
	same(t, component, "discount_filter.go")
	same(t, test, "discount_filter_test.go")
	same(t, dir, "")
}

func TestANameOfTheProjectIsThePackageOfARootDirectory(t *testing.T) {
	root := t.TempDir()
	_, _, _, pkg, _, _ := plannedIn(t, root, nil, ".", "discount_filter")
	same(t, pkg, goName(filepath.Base(root)))
}

func TestThePackageOfTheOtherGoFilesWins(t *testing.T) {
	_, _, _, pkg, _, _ := planned(t, map[string]string{"pricing.go": "package pricing\n"}, "src/pricing", "discount_filter")
	same(t, pkg, "pricing")
}

func TestADirectoryOfItsOwnIsNotInOtherDirectorysPackage(t *testing.T) {
	root := t.TempDir()
	_, _, _, pkg, _, _ := plannedIn(t, root, map[string]string{"src/pricing/pricing.go": "package pricing\n"},
		"src/pricing", "discount_filter")
	same(t, pkg, "pricing")
}

func TestThePathsOfADirectoryAreJoinedWithSlash(t *testing.T) {
	component, test, dir, _, code, _ := planned(t, nil, "src/pricing", "http_get_filter")
	same(t, code, 0)
	same(t, component, "src/pricing/http_get_filter.go")
	same(t, test, "src/pricing/http_get_filter_test.go")
	same(t, dir, "src/pricing")
}

func TestAPackageNameOfADirectoryDropsWhatGoCannotHave(t *testing.T) {
	same(t, directoryName("src/my-pricing.v2", "/tmp/x"), "mypricingv2")
	same(t, goName("codeupipe-add"), "codeupipeadd")
	same(t, validPackageName("pricing"), true)
	same(t, validPackageName("my-pack"), false)
	same(t, validPackageName("init"), false)
}

func TestThePackageClauseOfAFile(t *testing.T) {
	pkg, found := packageClause("// A note.\n\npackage pricing\n\nfunc F() {}\n")
	same(t, found, true)
	same(t, pkg, "pricing")
	_, found = packageClause("func F() {} // package inside the code\n")
	same(t, found, false)
	_, found = packageClause("// TODO: package the parts later\nvar x = 1\n")
	same(t, found, false)
}
