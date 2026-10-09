// Anonymous steps the C++ analyzer must flag (expect: comments name the rule).
#include <memory>
#include "codeupipe/codeupipe.hpp"

using namespace cup;

namespace app::filters {
struct Named final : IFilter {
    Payload call(const Payload& in) override { return in; }
};
inline Payload normalize(const Payload& p) { return p; }
}  // namespace app::filters

bool is_on(const Payload&) { return true; }

std::unique_ptr<IFilter> inc() {
    return make_filter([](const Payload& p) { return p; });
}

auto make_closure(int k) { return [k](const Payload&) { return k > 0; }; }

Pipeline build_child() {
    Pipeline p;
    p.add_filter(std::make_unique<app::filters::Named>(), "n");
    return p;
}

Pipeline build() {
    struct Local final : IFilter {
        Payload call(const Payload& in) override { return in; }
    };
    class LocalTap : public ITap {
    public:
        void observe(const Payload&) override {}
    };

    Pipeline pipe;
    pipe.add_filter(make_filter([](const Payload& p) { return p; }), "lambda"); // expect: CUP-A001
    pipe.add_filter(std::make_unique<Local>(), "local"); // expect: CUP-A003
    pipe.add_tap(std::make_unique<LocalTap>(), "tap"); // expect: CUP-A003
    pipe.add_filter(make_filter(&app::filters::normalize), "fn pointer"); // expect: CUP-A007
    pipe.add_filter(make_filter(app::filters::normalize), "fn name"); // expect: CUP-A007
    pipe.add_filter(std::make_unique<Valve>("v", std::make_unique<app::filters::Named>(),
                                            [](const Payload&) { return true; }), "valve"); // expect: CUP-A001
    pipe.add_filter(std::make_unique<Valve>("v", std::make_unique<Local>(), is_on), "valve2"); // expect: CUP-A003 CUP-A007
    pipe.add_filter(inc(), "factory"); // expect: CUP-A001

    auto pred = [](const Payload&) { return false; };
    auto gated = std::make_unique<Valve>("v", std::make_unique<app::filters::Named>(), pred); // expect: CUP-A001
    pipe.add_filter(std::move(gated), "gated");
    pipe.add_filter(std::make_unique<Valve>("v", std::make_unique<app::filters::Named>(), make_closure(1)), "c"); // expect: CUP-A001

    Pipeline inner;
    inner.add_filter(std::make_unique<app::filters::Named>(), "inner");
    pipe.add_pipeline(std::move(inner), "inner"); // expect: CUP-A005
    pipe.add_pipeline(Pipeline(), "empty"); // expect: CUP-A005
    auto child = build_child();
    pipe.add_pipeline(std::move(child), "child"); // expect: CUP-A005
    return pipe;
}
