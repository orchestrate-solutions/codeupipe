#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"
#include "steps.hpp"

using namespace cup;

TEST_CASE("State records each step with timing", "[state]") {
    Pipeline pipe;
    pipe.observe_timing(true);
    pipe.add_filter(cup_test::PassThrough{});
    pipe.add_filter(cup_test::PassThrough{});
    pipe.run(Payload{});
    REQUIRE(pipe.state().executed == std::vector<std::string>{"cup_test::PassThrough", "cup_test::PassThrough#2"});
    REQUIRE(pipe.state().timings.count("cup_test::PassThrough") == 1);
    REQUIRE(pipe.state().timings.count("cup_test::PassThrough#2") == 1);
}
