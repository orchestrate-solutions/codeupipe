// Step identity (conformance/API.md): a step is identified by its type's
// qualified name, #n from its second use; no names. Anonymous steps are
// refused at compile time (static_assert), so their detection is tested
// with static_assert too.
#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"

#include <regex>
#include <stdexcept>
#include <string>
#include <vector>

using namespace cup;

namespace cup_test {

struct Inc final : IFilter {
    Payload call(const Payload& p) override {
        return p.insert("n", Value(p.get("n", Value(0)).as_int().value_or(0) + 1));
    }
};

struct Boom final : IFilter {
    Payload call(const Payload&) override { throw std::runtime_error("boom"); }
};

struct Audit final : ITap {
    void observe(const Payload&) override {}
};

struct IsOn {
    bool test(const Payload& p) const { return p.get("on", Value(false)).as_bool().value_or(false); }
};

/// A configurable predicate: a predicate object, its settings in members.
struct AtLeast {
    std::int64_t n;
    bool test(const Payload& p) const { return p.get("n", Value(0)).as_int().value_or(0) >= n; }
};

/// A functor is not a predicate object: predicates have test().
struct CallOperatorOnly {
    bool operator()(const Payload&) const { return true; }
};

/// A named pipeline type: only Pipeline subclasses can be nested.
struct Onboarding : Pipeline {
    Onboarding() { add_filter(Inc{}); }
};

struct Record final : IHook {
    std::vector<std::string>* events;
    explicit Record(std::vector<std::string>* e) : events(e) {}
    void before(const std::string& s, const Payload&) override { events->push_back("before:" + s); }
    void after(const std::string& s, const Payload&) override { events->push_back("after:" + s); }
    void on_error(const std::string& s, const std::exception&, const Payload&) override { events->push_back("error:" + s); }
};

}  // namespace cup_test

namespace {
struct Hidden final : IFilter {
    Payload call(const Payload& p) override { return p; }
};
}  // namespace

using namespace cup_test;

TEST_CASE("identity is the qualified type name", "[identity]") {
    Pipeline pipe;
    pipe.add_filter(Inc{});
    pipe.run(Payload{});
    REQUIRE(pipe.state().executed == std::vector<std::string>{"cup_test::Inc"});
}

TEST_CASE("reuse is numbered from the second occurrence", "[identity]") {
    Pipeline pipe;
    pipe.add_filter(Inc{}).add_filter(Inc{}).add_filter(Inc{});
    REQUIRE(pipe.identities() == std::vector<std::string>{"cup_test::Inc", "cup_test::Inc#2", "cup_test::Inc#3"});
}

TEST_CASE("taps and hooks see identities", "[identity]") {
    std::vector<std::string> events;
    Pipeline pipe;
    pipe.add_filter(Inc{}).add_tap(Audit{}).add_filter(Boom{}).use_hook(std::make_unique<Record>(&events));
    REQUIRE_THROWS(pipe.run(Payload{}));
    REQUIRE(pipe.state().executed == std::vector<std::string>{"cup_test::Inc", "cup_test::Audit"});
    REQUIRE(events == std::vector<std::string>{"before:", "before:cup_test::Inc", "after:cup_test::Inc",
                                               "before:cup_test::Boom", "error:cup_test::Boom", "error:"});
}

TEST_CASE("a Valve is identified by its inner filter", "[identity]") {
    Pipeline pipe;
    pipe.add_filter(Valve(Inc{}, IsOn{}));
    pipe.run(Payload{});
    REQUIRE(pipe.state().skipped == std::vector<std::string>{"cup_test::Inc"});
}

TEST_CASE("a configurable predicate is a named functor", "[identity]") {
    Valve valve(Inc{}, AtLeast{5});
    REQUIRE(valve.predicate_symbol() == "cup_test::AtLeast");
    Pipeline pipe;
    pipe.add_filter(std::move(valve));
    REQUIRE(pipe.run(Payload{}.insert("n", Value(5))).get("n").as_int() == 6);
}

TEST_CASE("a named Pipeline subclass nests as one step", "[identity]") {
    Pipeline outer;
    outer.add_filter(Inc{}).add_pipeline(Onboarding{});
    REQUIRE(outer.run(Payload{}).get("n").as_int() == 2);
    REQUIRE(outer.state().executed == std::vector<std::string>{"cup_test::Inc", "cup_test::Onboarding"});
}

TEST_CASE("the add site is recorded", "[identity]") {
    Pipeline pipe;
    pipe.add_filter(Inc{});
    REQUIRE(std::regex_search(pipe.step_sites().at("cup_test::Inc"), std::regex(R"(test_step_identity\.cpp:\d+$)")));
}

TEST_CASE("anonymous steps are refused at compile time", "[identity]") {
    auto lambda = [](const Payload&) { return true; };
    static_assert(cup::detail::is_lambda<decltype(lambda)>());
    static_assert(!cup::detail::is_lambda<IsOn>());
    static_assert(cup::detail::in_anonymous_namespace<Hidden>());
    static_assert(!cup::detail::in_anonymous_namespace<Inc>());
    static_assert(!std::is_constructible_v<Valve, Inc, bool (*)(const Payload&)>,
                  "a function pointer predicate has no name: predicates are types");
    static_assert(!std::is_constructible_v<Valve, Inc, decltype(lambda)>, "a lambda is not a predicate object");
    static_assert(!std::is_constructible_v<Valve, Inc, CallOperatorOnly>, "predicates have test(), not operator()");
    static_assert(cup::PredicateObject<AtLeast>);
    SUCCEED("checked by static_assert");
}
