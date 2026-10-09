// The two CUP invariants — enforced by test.
#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"
#include "steps.hpp"

using namespace cup;

static Pipeline build_core() {
    Pipeline p;
    p.add_filter(cup_test::Increment{});
    p.add_filter(cup_test::Square{});
    return p;
}

TEST_CASE("Invariant 1: removing Taps yields identical output", "[invariant]") {
    auto bare = build_core();
    auto observed = build_core();
    observed.add_tap(cup_test::NoopTap{});

    auto a = bare.run(Payload{}.insert("n", Value{4}));
    auto b = observed.run(Payload{}.insert("n", Value{4}));
    REQUIRE(a == b);
}

TEST_CASE("Invariant 2: same input → same output (determinism)", "[invariant]") {
    auto pipe = build_core();
    auto in = Payload{}.insert("n", Value{9});
    REQUIRE(pipe.run(in) == pipe.run(in));
}
