#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"
#include "steps.hpp"

using namespace cup;

TEST_CASE("Filter transforms payload", "[filter]") {
    cup_test::Double double_it;
    Payload out = double_it.call(Payload{}.insert("n", Value{21}));
    REQUIRE(out.get("n").as_int() == 42);
}

namespace cup_test {
struct AddOne {
    Payload call(const Payload& p) const { return p.insert("n", Value{n_of(p) + 1}); }
};
}  // namespace cup_test

TEST_CASE("Filter concept — static dispatch", "[filter]") {
    static_assert(FilterConcept<cup_test::AddOne>);
    cup_test::AddOne f;
    auto out = f.call(Payload{}.insert("n", Value{9}));
    REQUIRE(out.get("n").as_int() == 10);
}
