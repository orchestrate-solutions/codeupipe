// codeupipe add for Go: make the files of a component (conformance/ADD.md).
// It has two dependencies: the codeupipe Go runtime, through a replace in
// this repository, and gopkg.in/yaml.v3, which reads a layout (--layout):
// Go has no YAML reader in its standard library (ADD.md, decision 3).
module github.com/orchestrate-solutions/codeupipe/packages/codeupipe-add-go

go 1.22

require (
	github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go v0.0.0
	gopkg.in/yaml.v3 v3.0.1
)

replace github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go => ../codeupipe-go
