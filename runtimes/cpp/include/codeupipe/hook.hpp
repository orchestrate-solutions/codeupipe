// codeupipe/hook.hpp — lifecycle observer
//
// `step` is the step's name; pipeline-level events pass the empty string.
// On a filter failure: on_error(step), then on_error("") (the pipeline).
// Taps get no hook events.

#pragma once

#include <exception>
#include <string>

#include "payload.hpp"

namespace cup {

class IHook {
public:
    virtual ~IHook() = default;
    virtual void before(const std::string& /*step*/, const Payload& /*p*/) {}
    virtual void after(const std::string& /*step*/, const Payload& /*p*/) {}
    virtual void on_error(const std::string& /*step*/, const std::exception& /*error*/, const Payload& /*p*/) {}
};

} // namespace cup
