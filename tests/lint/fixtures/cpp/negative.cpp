// Named steps the C++ analyzer must NOT flag.
#include <memory>
#include <vector>
#include "codeupipe/codeupipe.hpp"

#define ADD(p, f) p.add_filter(f, #f) /* a macro is blanked */

using namespace cup;

struct Named final : IFilter {
    Payload call(const Payload& in) override { return in; }
};

struct IsOn {
    bool operator()(const Payload&) const { return true; }
};

struct Onboarding : Pipeline {
    Onboarding() { add_filter(std::make_unique<Named>(), "n"); }
};

std::unique_ptr<IFilter> make_named() { return std::make_unique<Named>(); }

Pipeline build(std::vector<std::unique_ptr<IFilter>> steps) {
    Pipeline pipe;  // a plain pipeline at the top level is fine
    const char* text = "p.add_filter(make_filter([](auto p) { return p; }))";
    char quote = '"';
    int big = 1'000'000;
    pipe.add_filter(std::make_unique<Named>(), "a");
    pipe.add_filter(std::make_unique<Valve>("v", std::make_unique<Named>(), IsOn{}), "v");
    pipe.add_pipeline(Onboarding(), "onboarding");
    pipe.add_filter(make_named(), "factory");
    for (auto& s : steps) pipe.add_filter(std::move(s), "loop");
    int values[] = {1, 2, 3};
    auto doubled = values[0] * 2;  // subscripts are not lambdas
    std::sort(steps.begin(), steps.end(), [](auto& a, auto& b) { return a < b; });  // not a step
    (void)text; (void)quote; (void)big; (void)doubled;
    return pipe;
}
