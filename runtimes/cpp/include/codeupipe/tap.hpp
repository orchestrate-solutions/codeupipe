// codeupipe/tap.hpp — Tap: read-only observer (Plane B)
//
// observe() may throw. The Pipeline contains the failure: it is recorded in
// State::errors under the Tap's name and the run continues (a Tap failure
// never halts Plane A). The Tap's name is given when it is added.

#pragma once

#include <memory>
#include <utility>

#include "payload.hpp"

namespace cup {

class ITap {
public:
    virtual ~ITap() = default;
    virtual void observe(const Payload& p) = 0;
};

// No lambda adapter (TapFn/make_tap was one): taps are identified by their
// type (conformance/API.md, "Step identity"). Declare a struct.

} // namespace cup
