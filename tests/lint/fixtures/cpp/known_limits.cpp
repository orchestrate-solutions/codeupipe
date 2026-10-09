// What the lexical scan cannot see (packages/codeupipe-lint/README.md). Unflagged lines are
// false negatives; an expect comment marked (false positive) is one.
#include "codeupipe/codeupipe.hpp"
#include "other/filters.hpp"  // declares: int remote_fn(int);

using namespace cup;

struct Named final : IFilter {
    Payload call(const Payload& in) override { return in; }
};

Pipeline build() {
    Pipeline pipe;
    // A free function declared only in a header: its name is unknown here.
    pipe.add_filter(make_filter(remote_fn), "header function");
    // A lambda hidden behind a macro.
    pipe.add_filter(MAKE_LAMBDA_FILTER(), "macro");
    // Brace-initialized Valve is not recognised as a Valve.
    pipe.add_filter(std::unique_ptr<IFilter>(new Valve{"v", std::make_unique<Named>(), pred_from_elsewhere}), "brace");
    return pipe;
}

struct Configured final : IFilter {
    template <typename F> explicit Configured(F) {}
    Payload call(const Payload& in) override { return in; }
};

Pipeline build2() {
    Pipeline pipe;
    // A lambda anywhere in the argument counts, even as a named filter's
    // constructor argument.
    pipe.add_filter(std::make_unique<Configured>([](int x) { return x; }), "configured"); // expect: CUP-A001 (false positive)
    return pipe;
}
