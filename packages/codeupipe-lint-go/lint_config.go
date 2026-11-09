package codeupipelint

// LintConfig is the lint section of the config file. A nil list is a key
// that the file does not have.
type LintConfig struct {
	// Paths are the files or directories to check.
	Paths []string
	// Exclude holds globs of the files that are not checked.
	Exclude []string
	// Disable holds the rule ids that are switched off.
	Disable []string
}
