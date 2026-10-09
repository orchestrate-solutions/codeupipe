#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"
#include "steps.hpp"

#include <stdexcept>
#include <string>
#include <vector>

using namespace cup;

// Pipeline-level events use an empty step name and wrap the step-level ones;
// on a failure, on_error fires for the failing step and then the pipeline.
// Hooks receive step identities. Same contract in every runtime:
// conformance/cases/hook.json.
struct RecordHook : IHook {
    std::vector<std::string>* log;
    explicit RecordHook(std::vector<std::string>* l) : log(l) {}
    void before(const std::string& s, const Payload&) override { log->push_back("before:" + s); }
    void after (const std::string& s, const Payload&) override { log->push_back("after:" + s); }
    void on_error(const std::string& s, const std::exception&, const Payload&) override { log->push_back("error:" + s); }
};

TEST_CASE("Hook fires around the pipeline and each filter", "[hook]") {
    std::vector<std::string> log;
    Pipeline pipe;
    pipe.use_hook(std::make_unique<RecordHook>(&log));
    pipe.add_filter(cup_test::PassThrough{});
    pipe.add_filter(cup_test::PassThrough{});
    pipe.run(Payload{});

    const std::string a = "cup_test::PassThrough", b = "cup_test::PassThrough#2";
    REQUIRE(log == std::vector<std::string>{"before:", "before:" + a, "after:" + a, "before:" + b, "after:" + b, "after:"});
}

TEST_CASE("on_error fires for the failing step, then the pipeline", "[hook]") {
    std::vector<std::string> log;
    Pipeline pipe;
    pipe.use_hook(std::make_unique<RecordHook>(&log));
    pipe.add_filter(cup_test::PassThrough{});
    pipe.add_filter(cup_test::Throws{});

    REQUIRE_THROWS_AS(pipe.run(Payload{}), std::runtime_error);
    const std::string a = "cup_test::PassThrough", b = "cup_test::Throws";
    REQUIRE(log == std::vector<std::string>{"before:", "before:" + a, "after:" + a, "before:" + b, "error:" + b, "error:"});
}
