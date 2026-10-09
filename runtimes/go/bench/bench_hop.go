// Go native hop bench — matches cpp schema.
// Build: cd runtimes/go/bench && go build -o bench_hop
// Run:   ./bench_hop [filters] [iters]
package main

import (
	"fmt"
	"os"
	"strconv"
	"time"

	cup "github.com/codeuchain/codeupipe-core/codeupipe"
)

type inc struct{ name string }

func (i *inc) Call(p cup.Payload) (cup.Payload, error) {
	n, _ := p.Get("n").(int64)
	return p.Insert("n", n+1), nil
}
func (i *inc) Name() string { return i.name }

func atoi(s string, dflt int) int {
	if s == "" {
		return dflt
	}
	v, err := strconv.Atoi(s)
	if err != nil {
		return dflt
	}
	return v
}

func main() {
	filters := 8
	iters := 200000
	if len(os.Args) > 1 {
		filters = atoi(os.Args[1], filters)
	}
	if len(os.Args) > 2 {
		iters = atoi(os.Args[2], iters)
	}

	pipe := cup.NewPipeline()
	for i := 0; i < filters; i++ {
		pipe.AddFilter(&inc{name: fmt.Sprintf("inc_%d", i)})
	}
	pipe = pipe.ObserveState(false)

	seed := cup.NewPayload(map[string]any{"n": int64(0)})
	for i := 0; i < 1000; i++ {
		_, _ = pipe.Run(seed)
	}

	t0 := time.Now()
	var out cup.Payload = seed
	for i := 0; i < iters; i++ {
		out, _ = pipe.Run(seed)
	}
	nsTotal := time.Since(t0).Nanoseconds()
	nsPerIter := float64(nsTotal) / float64(iters)
	nsPerHop := nsPerIter / float64(filters)
	finalN, _ := out.Get("n").(int64)
	fmt.Printf(
		"{\"runtime\":\"go\",\"variant\":\"sync\",\"filters\":%d,\"iterations\":%d,"+
			"\"ns_per_iter\":%.2f,\"ns_per_hop\":%.2f,\"ops_per_sec\":%.0f,\"final_n\":%d}\n",
		filters, iters, nsPerIter, nsPerHop, 1e9/nsPerIter, finalN,
	)
}
