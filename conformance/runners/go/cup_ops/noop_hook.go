package cup_ops

import "github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"

// NoopHook is a Hook that does nothing: the cost of having one.
type NoopHook struct {
	codeupipe.HookBase
}
