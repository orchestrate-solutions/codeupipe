#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"
#include "steps.hpp"

using namespace cup;

TEST_CASE("Tap observes but does not mutate", "[tap]") {
    int observed = 0;
    Pipeline pipe;
    pipe.add_filter(cup_test::Set("n", Value{7}));
    pipe.add_tap(cup_test::WatchN(&observed));

    auto out = pipe.run(Payload{});
    REQUIRE(observed == 7);
    REQUIRE(out.get("n").as_int() == 7);
}

TEST_CASE("a failing Tap never halts the pipeline", "[tap]") {
    Pipeline pipe;
    pipe.add_filter(cup_test::PassThrough{});
    pipe.add_tap(cup_test::ThrowingTap{});
    // Must NOT throw
    REQUIRE_NOTHROW(pipe.run(Payload{}));
    REQUIRE(pipe.state().errors.size() == 1);
}
