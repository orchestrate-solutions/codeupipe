package codeupipe

// StepFailure is an error that State keeps: the label of the step that
// failed, and the error itself.
type StepFailure struct {
	Label string
	Err   error
}
