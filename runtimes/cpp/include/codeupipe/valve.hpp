// codeupipe/valve.hpp — Conditional flow control
//
// Valve(inner, predicate). When the predicate is false the payload passes
// through unchanged and the step is recorded as skipped. A Valve is
// identified by its inner filter (conformance/API.md, "Step identity").
// The predicate is an object (conformance/API.md, "Valve"): a named type
// with `bool test(const Payload&) const`, configuration in its members. A
// lambda or a function pointer has no test(), so either is a compile error.

#pragma once

#include <functional>
#include <memory>
#include <string>
#include <type_traits>
#include <utility>

#include "filter.hpp"
#include "payload.hpp"
#include "step_identity.hpp"

namespace cup {

/// A predicate object: a type with `bool test(const Payload&) const`.
template <typename P>
concept PredicateObject = std::is_class_v<P> && requires(const P& p, const Payload& payload) {
    { p.test(payload) } -> std::convertible_to<bool>;
};

class Valve final : public IFilter {
public:
    template <typename F, PredicateObject P,
              typename = std::enable_if_t<std::is_base_of_v<IFilter, F>>>
    Valve(F inner, P predicate)
        : inner_identity_(detail::identity_of<F>()),
          predicate_symbol_(detail::identity_of<P>()),
          inner_(std::make_unique<F>(std::move(inner))),
          predicate_([p = std::move(predicate)](const Payload& payload) { return p.test(payload); }) {}

    Payload call(const Payload& in) override {
        if (predicate_(in)) {
            last_skipped_ = false;
            return inner_->call(in);
        }
        last_skipped_ = true;
        return in;
    }

    bool last_skipped() const noexcept override { return last_skipped_; }
    /// The inner filter's identity: the Valve's identity as a step.
    const std::string& inner_identity() const noexcept { return inner_identity_; }
    /// The predicate's identity (detail).
    const std::string& predicate_symbol() const noexcept { return predicate_symbol_; }

private:
    std::string                          inner_identity_;
    std::string                          predicate_symbol_;
    std::unique_ptr<IFilter>             inner_;
    std::function<bool(const Payload&)>  predicate_;
    bool                                 last_skipped_ = false;
};

} // namespace cup
