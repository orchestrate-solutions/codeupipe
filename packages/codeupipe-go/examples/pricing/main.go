// go run ./examples/pricing: run the pipeline with a Hook and show its State.
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

func main() {
	pipeline := codeupipe.NewNamedPipeline(PricingPipeline{})
	pipeline.UseHook(PrintStepsHook{})

	fmt.Println("steps:")
	result, err := pipeline.Run(context.Background(), codeupipe.NewPayload(map[string]any{"price": 100, "qty": 12}))
	if err != nil {
		log.Fatal(err)
	}

	state := pipeline.State()
	fmt.Println("result:  ", result.ToDict())
	fmt.Println("executed:", state.Executed())
	fmt.Println("skipped: ", state.Skipped())
	fmt.Println("errors:  ", state.Errors())
}
