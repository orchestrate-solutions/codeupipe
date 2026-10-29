// The Go conformance runner: go run . <target> < cases.json > results.json.
// It has no dependency to download: the runtime is the package of this
// repository, by the replace below.
module github.com/orchestrate-solutions/codeupipe/conformance/runners/go

go 1.22

require github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go v0.0.0

replace github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go => ../../../packages/codeupipe-go
