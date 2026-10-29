package codeupipe

import "context"

// TapOf reads the data of a pipeline that carries P as it goes by. It does
// not write to it. A failure never stops the run: State records the error
// under the label of the Tap, and Hooks are not told.
type TapOf[P any] interface {
	Observe(ctx context.Context, payload P) error
}

// Tap reads the Payload as it goes by, to log it or to send it somewhere.
type Tap = TapOf[*Payload]
