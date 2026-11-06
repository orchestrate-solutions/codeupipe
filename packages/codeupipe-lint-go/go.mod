// codeupipe-lint for Go. It has no dependency to download: the runtime is
// the package of this repository, by the replace below, and Go's own
// go/parser and go/ast read the source.
module github.com/orchestrate-solutions/codeupipe/packages/codeupipe-lint-go

go 1.22

require github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go v0.0.0

replace github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go => ../codeupipe-go
