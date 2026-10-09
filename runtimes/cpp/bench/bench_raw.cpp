// bench_raw.cpp — Pure C++ baseline. No CUP, no Payload, no shared_ptr.
// Same logical work as bench_hop: N increments per iteration, M iterations.
//
// Three variants isolate where CUP's overhead comes from:
//   scalar   : plain int64, N inlined increments  (theoretical floor)
//   map      : unordered_map<string,Value>, mutated in place  (no COW, no vtbl)
//   map_cow  : same map, but full copy at each step  (mimics CUP's COW cost)

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <variant>

using clk = std::chrono::steady_clock;
using Value = std::variant<std::monostate, bool, std::int64_t, double, std::string>;
using Map   = std::unordered_map<std::string, Value>;

int main(int argc, char** argv) {
    int filters = argc > 1 ? std::atoi(argv[1]) : 8;
    int iters   = argc > 2 ? std::atoi(argv[2]) : 100000;

    volatile std::int64_t sink = 0;

    auto emit = [&](const char* name, long ns_total) {
        double ns_per_iter = double(ns_total) / iters;
        double ns_per_hop  = ns_per_iter / filters;
        double ops         = 1e9 / ns_per_iter;
        std::printf(
            "{\"runtime\":\"cpp-raw\",\"variant\":\"%s\",\"filters\":%d,\"iterations\":%d,"
            "\"ns_per_iter\":%.2f,\"ns_per_hop\":%.2f,\"ops_per_sec\":%.0f}\n",
            name, filters, iters, ns_per_iter, ns_per_hop, ops
        );
    };

    // scalar
    for (int i = 0; i < 1000; ++i) { std::int64_t n = 0; for (int k = 0; k < filters; ++k) ++n; sink = n; }
    auto t0 = clk::now();
    for (int i = 0; i < iters; ++i) {
        std::int64_t n = 0;
        for (int k = 0; k < filters; ++k) ++n;
        sink = n;
    }
    emit("scalar", std::chrono::duration_cast<std::chrono::nanoseconds>(clk::now() - t0).count());

    // map (in-place mutation)
    auto do_map = [&](std::int64_t& out) {
        Map m;
        m["n"] = std::int64_t{0};
        for (int k = 0; k < filters; ++k) {
            std::get<std::int64_t>(m["n"]) += 1;
        }
        out = std::get<std::int64_t>(m["n"]);
    };
    for (int i = 0; i < 1000; ++i) { std::int64_t x; do_map(x); sink = x; }
    t0 = clk::now();
    for (int i = 0; i < iters; ++i) { std::int64_t x; do_map(x); sink = x; }
    emit("map", std::chrono::duration_cast<std::chrono::nanoseconds>(clk::now() - t0).count());

    // map_cow (full-copy per step, no shared_ptr wrapper)
    auto do_cow = [&](std::int64_t& out) {
        Map m;
        m["n"] = std::int64_t{0};
        for (int k = 0; k < filters; ++k) {
            Map next = m;
            std::get<std::int64_t>(next["n"]) += 1;
            m = std::move(next);
        }
        out = std::get<std::int64_t>(m["n"]);
    };
    for (int i = 0; i < 1000; ++i) { std::int64_t x; do_cow(x); sink = x; }
    t0 = clk::now();
    for (int i = 0; i < iters; ++i) { std::int64_t x; do_cow(x); sink = x; }
    emit("map_cow", std::chrono::duration_cast<std::chrono::nanoseconds>(clk::now() - t0).count());

    (void)sink;
    return 0;
}
