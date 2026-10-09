#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"
#include "steps.hpp"

using namespace cup;

TEST_CASE("Valve gates a filter by predicate", "[valve]") {
    // Valve(inner, predicate): identified by its inner filter; the predicate
    // is a named functor type
    Pipeline pipe;
    pipe.add_filter(Valve(cup_test::AddHundred{}, cup_test::Positive{}));

    // Predicate true → runs
    auto pos = pipe.run(Payload{}.insert("n", Value{5}));
    REQUIRE(pos.get("n").as_int() == 105);
    REQUIRE(pipe.state().executed == std::vector<std::string>{"cup_test::AddHundred"});

    // Predicate false → passthrough
    auto neg = pipe.run(Payload{}.insert("n", Value{-5}));
    REQUIRE(neg.get("n").as_int() == -5);
    REQUIRE(pipe.state().skipped == std::vector<std::string>{"cup_test::AddHundred"});
}
