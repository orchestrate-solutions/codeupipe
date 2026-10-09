// examples/clean_validate_save — mirrors the canonical Python example.
//
//   raw_text → clean → validate → save

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <stdexcept>
#include <string>

#include "codeupipe/codeupipe.hpp"

using namespace cup;

static std::string trim(std::string s) {
    auto not_space = [](unsigned char c) { return !std::isspace(c); };
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), not_space));
    s.erase(std::find_if(s.rbegin(), s.rend(), not_space).base(), s.end());
    return s;
}

// Steps are named types: each is identified by its type (conformance/API.md,
// "Step identity"), e.g. "app::Clean" in the pipeline's State.
namespace app {
struct Clean final : IFilter {
    Payload call(const Payload& p) override {
        auto raw = p.get("raw_text").as_string();
        return p.insert("text", Value{raw ? trim(*raw) : std::string{}});
    }
};
struct Validate final : IFilter {
    Payload call(const Payload& p) override {
        auto t = p.get("text").as_string();
        if (!t || t->empty()) throw std::runtime_error("empty text");
        return p;
    }
};
struct Save final : IFilter {
    Payload call(const Payload& p) override { return p.insert("saved_id", Value{std::int64_t{42}}); }
};
}  // namespace app

int main() {
    Pipeline pipe;
    pipe.add_filter(app::Clean{}).add_filter(app::Validate{}).add_filter(app::Save{});

    auto out = pipe.run(Payload{}.insert("raw_text", Value{"  hello  "}));
    std::printf("saved_id=%lld text='%s'\n",
        static_cast<long long>(out.get("saved_id").as_int().value_or(-1)),
        out.get("text").as_string()->c_str());
    return 0;
}
