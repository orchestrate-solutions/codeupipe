// codeupipe/filter.hpp — Filter: Payload in, Payload out
//
// A Filter is a pure-ish transformation. Its name is given when it is added
// to a Pipeline (conformance/API.md), not carried by the filter.

#pragma once

#include <concepts>
#include <memory>
#include <utility>

#include "payload.hpp"

namespace cup {

template <typename F>
concept FilterConcept = requires(F f, Payload p) {
    { f.call(p) } -> std::same_as<Payload>;
};

// Type-erased interface for Pipeline composition
class IFilter {
public:
    virtual ~IFilter() = default;
    virtual Payload call(const Payload& in) = 0;
    // A Valve reports whether its last call skipped the inner filter, so the
    // Pipeline can record the step as skipped rather than executed.
    virtual bool last_skipped() const noexcept { return false; }
};

// Adapter: wrap any callable (lambda, function, FilterConcept) as IFilter
// No lambda adapter (FilterFn/make_filter was one): a step is identified by
// its type (conformance/API.md, "Step identity"), and a wrapper around a
// lambda would give every lambda the wrapper's identity. Declare a struct.

} // namespace cup
