// codeupipe/state.hpp — what happened in the last run (kept OUT of Payload)
//
// executed / skipped (names, in order), errors (name + the error), timings
// (seconds, when timing is on). A run resets State; a failed run keeps the
// steps that completed before the failure. Filters are blind to State.

#pragma once

#include <exception>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace cup {

struct StepError {
    std::string        name;
    std::exception_ptr error;    // the error itself
    std::string        message;  // error.what(), for convenience
};

class State {
public:
    std::vector<std::string>                executed;
    std::vector<std::string>                skipped;
    std::vector<StepError>                  errors;
    std::unordered_map<std::string, double> timings;

    void mark_executed(const std::string& name) { executed.push_back(name); }
    void mark_skipped(const std::string& name) { skipped.push_back(name); }
    void record_error(const std::string& name, std::exception_ptr error, std::string message) {
        errors.push_back(StepError{name, std::move(error), std::move(message)});
    }
    void record_timing(const std::string& name, double seconds) { timings[name] = seconds; }
    bool has_errors() const noexcept { return !errors.empty(); }

    // Start a new run. Clearing keeps the vectors' capacity, so steady-state
    // runs record State without allocating.
    void reset() {
        executed.clear();
        skipped.clear();
        errors.clear();
        timings.clear();
    }
};

} // namespace cup
