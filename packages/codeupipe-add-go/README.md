# codeupipe add for Go

`codeupipe add` makes the files of one component: its file and its test
(conformance/ADD.md). This is the Go command. It writes Go.

```bash
go run ./codeupipe-add filter Discount
go run ./codeupipe-add predicate at_least src/pricing --description "Says yes at a minimum."
```

In the root of a Go project, it makes `<dir>/discount_filter.go` and
`<dir>/discount_filter_test.go`, prints each path, and writes nothing when a
file exists. Exit code: 0 the files are made, 1 a file exists, 2 the arguments
cannot be used.

| Kind | What it makes |
|---|---|
| `filter` | `type DiscountFilter struct{}` with `Call(ctx, payload)` that returns nil |
| `predicate` | `type AtLeastPredicate struct{}` with `Test(ctx, payload)` that answers false |
| `tap` | `type AuditTap struct{}` with `Observe(ctx, payload)` that does nothing |
| `hook` | `type PrintStepsHook struct{ codeupipe.HookBase }` that does nothing at each event |
| `pipeline` | `type PricingPipeline struct{}` with `AddSteps(pipeline)` that adds no step |

The test is beside the component, in the package of the component, as Go
wants it, so it needs no import. Its one test fails on purpose, with
`Write the acceptance case for <TypeName>.`, so the work starts at RED.

The package of the new files is the package of the other `.go` files in the
directory, or else the name of the directory (ADD.md, "Rust and Go: the
package").

## How it is made

`codeupipe-add/` is the command: a codeupipe pipeline of six Filters, one in
each file, run by `main.go`.

| Step | What it does |
|---|---|
| `ParseArgumentsFilter` | the arguments to kind, name, directory, description |
| `TypeNameFilter` | kind and name to `DiscountFilter` and `discount_filter` |
| `PlanFilesFilter` | the two paths, and the package of the component |
| `RefuseExistingFilter` | a file that exists stops the run (exit 1) |
| `RenderFilesFilter` | the text of the two files |
| `WriteFilesFilter` | the files, and the directories that they need |

A step that cannot go on returns a `Refusal`, which stops the run with the
exit code of the contract, so the command writes both files or neither.

## Development

```bash
go test ./codeupipe-add/
go vet ./...
gofmt -l .
```

The cases of the contract judge it: `python conformance/add.py go:add`.

The folder `cmd/` holds the same entry text with a `//go:build ignore` tag:
the entry of the command is one file, `codeupipe-add/main.go`, and the Go
tool needs a buildable folder here.

## License

Apache License 2.0.
