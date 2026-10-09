#include <catch2/catch_test_macros.hpp>
#include "codeupipe/codeupipe.hpp"

using namespace cup;

TEST_CASE("Payload is immutable — insert returns a new Payload", "[payload]") {
    Payload p1;
    Payload p2 = p1.insert("k", Value{42});
    REQUIRE(p1.size() == 0);
    REQUIRE(p2.size() == 1);
    REQUIRE(p2.get("k").as_int() == 42);
}

TEST_CASE("Payload get with fallback", "[payload]") {
    Payload p;
    auto v = p.get("missing", Value{"default"});
    REQUIRE(v.as_string() != nullptr);
    REQUIRE(*v.as_string() == "default");
}

TEST_CASE("Payload merge preserves original", "[payload]") {
    Payload p = Payload{}.insert("a", Value{1});
    Payload q = p.merge(Payload(ValueMap{{"b", Value{2}}, {"c", Value{3}}}));
    REQUIRE(p.size() == 1);
    REQUIRE(q.size() == 3);
    REQUIRE(q.get("a").as_int() == 1);
    REQUIRE(q.get("b").as_int() == 2);
}

TEST_CASE("Value variants round-trip", "[payload]") {
    Value vb{true};   REQUIRE(vb.as_bool()   == true);
    Value vi{42};     REQUIRE(vi.as_int()    == 42);
    Value vf{3.14};   REQUIRE(vf.as_float()  == 3.14);
    Value vs{"hi"};   REQUIRE(*vs.as_string() == "hi");
    Value vn{nullptr}; REQUIRE(vn.is_null());
}
