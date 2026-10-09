#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"
#include "steps.hpp"

using namespace cup;

TEST_CASE("Pipeline runs filters in order", "[pipeline]") {
    Pipeline pipe;
    pipe.observe_timing(true);
    pipe.add_filter(cup_test::Increment{});
    pipe.add_filter(cup_test::Double{});

    Payload out = pipe.run(Payload{}.insert("n", Value{3}));
    REQUIRE(out.get("n").as_int() == 8);
    REQUIRE(pipe.state().executed == std::vector<std::string>{"cup_test::Increment", "cup_test::Double"});
    REQUIRE(pipe.state().timings.size() == 2);
    REQUIRE(pipe.state().errors.empty());
}

TEST_CASE("Pipeline blueprint is inspectable", "[pipeline]") {
    Pipeline pipe;
    pipe.add_filter(cup_test::PassThrough{});
    pipe.add_filter(cup_test::PassThrough{});
    REQUIRE(pipe.step_count() == 2);
    REQUIRE(pipe.identities() == std::vector<std::string>{"cup_test::PassThrough", "cup_test::PassThrough#2"});
}
