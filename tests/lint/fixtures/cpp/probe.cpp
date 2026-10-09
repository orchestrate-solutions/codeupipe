// Step-identity probe cases, with describe(label, f) replaced by a
// pipeline add call: the probe's cases as lint fixtures.
#include <string_view>

namespace app::filters {
struct Validate { int call(int p) const { return p; } };
inline int normalize(int p) { return p; }
}

auto make_closure(int k) { return [k](int p) { return p + k; }; }

int main() {
    struct Local { int call(int p) const { return p; } };
    cup::Pipeline p;
    p.add_filter(app::filters::Validate{}, "struct");
    p.add_filter(app::filters::Validate{}, "same struct again");
    p.add_filter(&app::filters::normalize, "function pointer"); // expect: CUP-A007
    p.add_filter([](int p) { return p; }, "lambda"); // expect: CUP-A001
    p.add_filter(make_closure(1), "returned lambda"); // expect: CUP-A001
    p.add_filter(Local{}, "struct defined in a function"); // expect: CUP-A003
}
