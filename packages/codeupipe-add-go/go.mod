// codeupipe add for Go: make the files of a component (conformance/ADD.md).
// It has one dependency: the codeupipe Go runtime, through a replace in this
// repository, so the conformance judge needs no download.
module github.com/orchestrate-solutions/codeupipe/packages/codeupipe-add-go

go 1.22

require github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go v0.0.0

replace github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go => ../codeupipe-go

