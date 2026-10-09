// Shared test steps. Steps are named types in a named namespace: a step is
// identified by its type (conformance/API.md, "Step identity"), and lambdas
// or anonymous-namespace types have no identity.
#pragma once

#include <stdexcept>
#include <string>

#include "codeupipe/codeupipe.hpp"

namespace cup_test {
using cup::IFilter;
using cup::ITap;
using cup::Payload;
using cup::Value;

inline std::int64_t n_of(const Payload& p) { return p.get("n", Value(0)).as_int().value_or(0); }

struct PassThrough final : IFilter {
    Payload call(const Payload& p) override { return p; }
};
struct Increment final : IFilter {
    Payload call(const Payload& p) override { return p.insert("n", Value{n_of(p) + 1}); }
};
struct Double final : IFilter {
    Payload call(const Payload& p) override { return p.insert("n", Value{n_of(p) * 2}); }
};
struct Square final : IFilter {
    Payload call(const Payload& p) override { return p.insert("n", Value{n_of(p) * n_of(p)}); }
};
struct AddHundred final : IFilter {
    Payload call(const Payload& p) override { return p.insert("n", Value{n_of(p) + 100}); }
};
struct Set final : IFilter {
    std::string key;
    Value value;
    Set(std::string k, Value v) : key(std::move(k)), value(std::move(v)) {}
    Payload call(const Payload& p) override { return p.insert(key, value); }
};
struct Throws final : IFilter {
    Payload call(const Payload&) override { throw std::runtime_error("boom"); }
};
struct NoopTap final : ITap {
    void observe(const Payload&) override {}
};
struct ThrowingTap final : ITap {
    void observe(const Payload&) override { throw std::runtime_error("sink down"); }
};
/// Records n into *seen: configuration (the pointer) lives in the member.
struct WatchN final : ITap {
    int* seen;
    explicit WatchN(int* s) : seen(s) {}
    void observe(const Payload& p) override { *seen = static_cast<int>(n_of(p)); }
};
// Predicate objects: test(), identified by their type.
struct Positive {
    bool test(const Payload& p) const { return n_of(p) > 0; }
};
struct Always {
    bool test(const Payload&) const { return true; }
};
struct Never {
    bool test(const Payload&) const { return false; }
};
/// A named pipeline type, so it can be nested.
struct SubPipeline : cup::Pipeline {};

}  // namespace cup_test
