// The CUP API contract, C++ side (conformance/API.md). Cross-runtime
// semantics are in conformance/cases; these pin the C++ spellings.
#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"

#include <stdexcept>
#include <string>
#include <vector>

using namespace cup;

#include "steps.hpp"

using cup_test::Increment;
using cup_test::Set;

TEST_CASE("steps are identified by their type", "[contract]") {
    Pipeline pipe;
    pipe.add_filter(Increment{}).add_filter(Increment{});
    pipe.run(Payload{});
    REQUIRE(pipe.state().executed == std::vector<std::string>{"cup_test::Increment", "cup_test::Increment#2"});
}

TEST_CASE("Valve(inner, predicate) records a skip", "[contract]") {
    Pipeline pipe;
    pipe.add_filter(Valve(Set("x", Value(1)), cup_test::Always{}));
    pipe.add_filter(Valve(Set("y", Value(1)), cup_test::Never{}));
    auto out = pipe.run(Payload{});
    REQUIRE(out.has("x"));
    REQUIRE_FALSE(out.has("y"));
    REQUIRE(pipe.state().executed == std::vector<std::string>{"cup_test::Set"});
    REQUIRE(pipe.state().skipped == std::vector<std::string>{"cup_test::Set#2"});
}

TEST_CASE("a failing Tap is recorded and never halts the pipeline", "[contract]") {
    Pipeline pipe;
    pipe.add_filter(Set("a", Value(1)));
    pipe.add_tap(cup_test::ThrowingTap{});
    pipe.add_filter(Set("b", Value(2)));
    auto out = pipe.run(Payload{});
    REQUIRE(out.has("b"));
    REQUIRE(pipe.state().executed ==
            std::vector<std::string>{"cup_test::Set", "cup_test::ThrowingTap", "cup_test::Set#2"});
    REQUIRE(pipe.state().errors.size() == 1);
    REQUIRE(pipe.state().errors[0].name == "cup_test::ThrowingTap");
}

TEST_CASE("a nested pipeline is one step", "[contract]") {
    cup_test::SubPipeline inner;
    inner.add_filter(Increment{});
    Pipeline pipe;
    pipe.add_filter(Increment{}).add_pipeline(std::move(inner));
    auto out = pipe.run(Payload{});
    REQUIRE(out.get("n").as_int() == 2);
    REQUIRE(pipe.state().executed == std::vector<std::string>{"cup_test::Increment", "cup_test::SubPipeline"});
}

TEST_CASE("on_error(step, error, payload) gets the error itself", "[contract]") {
    struct Record : IHook {
        std::string message;
        void on_error(const std::string& step, const std::exception& e, const Payload&) override {
            if (!step.empty()) message = e.what();
        }
    };
    auto hook = std::make_unique<Record>();
    auto* raw = hook.get();
    Pipeline pipe;
    pipe.use_hook(std::move(hook));
    pipe.add_filter(cup_test::Throws{});
    REQUIRE_THROWS(pipe.run(Payload{}));
    REQUIRE(raw->message == "boom");
}

TEST_CASE("Payload vocabulary", "[contract]") {
    Payload p(ValueMap{{"a", Value(nullptr)}, {"b", Value(2)}});
    REQUIRE(p.has("a"));
    REQUIRE(p.remove("a").to_dict().size() == 1);
    REQUIRE(p.merge(Payload(ValueMap{{"b", Value(3)}})).get("b").as_int() == 3);
    auto traced = p.with_trace("t-1");
    REQUIRE(traced.trace_id() == std::optional<std::string>("t-1"));
    REQUIRE_FALSE(p.trace_id().has_value());

    auto m = p.with_mutation();
    m.set("k", Value("v"));
    m.remove("b");
    auto back = m.to_immutable();
    REQUIRE(back.has("k"));
    REQUIRE_FALSE(back.has("b"));
    REQUIRE(back.trace_id() == p.trace_id());
}
