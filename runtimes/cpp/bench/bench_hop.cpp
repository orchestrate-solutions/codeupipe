// bench_hop.cpp — micro-benchmark: N filters × M iterations.
// Emits JSON lines for the polyglot bench matrix.

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>

#include "codeupipe/codeupipe.hpp"

using namespace cup;
using clk = std::chrono::steady_clock;

namespace bench {
struct Inc final : IFilter {
    Payload call(const Payload& x) override {
        return x.insert("n", Value{x.get("n").as_int().value_or(0) + 1});
    }
};
}  // namespace bench

static Pipeline build(int filters) {
    Pipeline p;
    for (int i = 0; i < filters; ++i) p.add_filter(bench::Inc{});
    return p;
}

static void run_variant(const char* variant, Pipeline& pipe, int filters, int iters) {
    Payload seed = Payload{}.insert("n", Value{std::int64_t{0}});
    for (int i = 0; i < 1000; ++i) pipe.run(seed);   // warm-up
    auto t0 = clk::now();
    Payload out = seed;
    for (int i = 0; i < iters; ++i) out = pipe.run(seed);
    auto ns_total = std::chrono::duration_cast<std::chrono::nanoseconds>(clk::now() - t0).count();
    double ns_per_iter = double(ns_total) / iters;
    double ns_per_hop  = ns_per_iter / filters;
    std::printf(
        "{\"runtime\":\"cpp\",\"variant\":\"%s\",\"filters\":%d,\"iterations\":%d,"
        "\"ns_per_iter\":%.2f,\"ns_per_hop\":%.2f,\"ops_per_sec\":%.0f,\"final_n\":%lld}\n",
        variant, filters, iters, ns_per_iter, ns_per_hop,
        1e9 / ns_per_iter,
        static_cast<long long>(out.get("n").as_int().value_or(0))
    );
}

int main(int argc, char** argv) {
    int filters = argc > 1 ? std::atoi(argv[1]) : 8;
    int iters   = argc > 2 ? std::atoi(argv[2]) : 200000;

    { auto p = build(filters);                            run_variant("fast",     p, filters, iters); }
    { auto p = build(filters); p.observe_timing(true);    run_variant("observed", p, filters, iters); }
    return 0;
}
