package main

import (
	"context"
	"runtime"
	"sort"
	"time"

	"github.com/orchestrate-solutions/codeupipe/packages/codeupipe-go"
)

// The bench mode times the scenarios as the Python and Rust runners do, so
// that conformance/bench.py can put the numbers side by side.

const (
	warmup  = 20_000
	runs    = 20_000
	repeats = 5
)

var referenceKeys = [10]string{"k0", "k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9"}

//go:noinline
func referenceWrite(data map[string]float64, key string) {
	data[key]++
}

// reference is the reference workload: ten map writes behind ten function
// calls, with no framework. A pipeline's time is reported relative to it.
func reference() map[string]float64 {
	data := map[string]float64{"a": 1}
	for _, key := range referenceKeys {
		referenceWrite(data, key)
	}
	return data
}

func timed(f func()) time.Duration {
	started := time.Now()
	for i := 0; i < runs; i++ {
		f()
	}
	return time.Since(started)
}

// measure gives µs per run, the best of repeats × runs, and the time
// relative to the reference workload. Each repeat times the reference and
// then f, back to back, and the median of the ratios is given.
func measure(f func()) (float64, float64) {
	// runtime.KeepAlive keeps each result, so that the compiler cannot drop the work.
	referenceRun := func() { runtime.KeepAlive(reference()) }
	for i := 0; i < warmup; i++ {
		f()
		referenceRun()
	}
	best := time.Duration(1<<63 - 1)
	ratios := make([]float64, 0, repeats)
	for i := 0; i < repeats; i++ {
		ref := timed(referenceRun)
		elapsed := timed(f)
		ratios = append(ratios, elapsed.Seconds()/ref.Seconds())
		if elapsed < best {
			best = elapsed
		}
	}
	sort.Float64s(ratios)
	return best.Seconds() / runs * 1e6, ratios[repeats/2]
}

// bench times one scenario. pipeline is built from its steps; input is its
// input.
func bench(id any, pipeline *codeupipe.Pipeline, input *codeupipe.Payload) map[string]any {
	ctx := context.Background()
	output, err := pipeline.Run(ctx, input)
	if err != nil {
		return map[string]any{"id": id, "unsupported": "the scenario fails: " + err.Error()}
	}
	usPerRun, relative := measure(func() {
		out, _ := pipeline.Run(ctx, input)
		runtime.KeepAlive(out)
	})
	return map[string]any{
		"id":         id,
		"us_per_run": usPerRun,
		"relative":   relative,
		"output":     output.ToDict(),
	}
}
