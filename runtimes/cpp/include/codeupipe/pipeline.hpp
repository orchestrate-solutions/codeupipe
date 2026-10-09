// codeupipe/pipeline.hpp — The orchestrator
//
// A Pipeline holds an ordered list of steps (Filters, Valves, Taps, nested
// Pipelines), each identified by its type (conformance/API.md, "Step
// identity", step_identity.hpp). It threads a Payload through them, records what ran in
// State, and fires Hooks at each step boundary. conformance/API.md.
//
// Perf notes:
//   - Timing is OPT-IN (observe_timing = false by default).
//   - Hook loops are branch-elided when hooks_.empty().
//   - Payload is moved between steps, not copied.
//
// Invariant 1: Removing all Taps and Hooks yields the identical output.
// Invariant 2: Same Payload in, same Payload out. Deterministic.

#pragma once

#include <chrono>
#include <map>
#include <memory>
#include <source_location>
#include <type_traits>
#include <stdexcept>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "filter.hpp"
#include "hook.hpp"
#include "payload.hpp"
#include "state.hpp"
#include "step_identity.hpp"
#include "tap.hpp"
#include "valve.hpp"

namespace cup {

class Pipeline {
public:
    Pipeline() = default;
    Pipeline(Pipeline&&) noexcept = default;
    Pipeline& operator=(Pipeline&&) noexcept = default;
    // Virtual: a nested pipeline is a named subclass, owned through Pipeline.
    virtual ~Pipeline() = default;

    // add_* are templates over the concrete step type, whose name is the
    // step's identity; #n from its second use. The add call's file:line is
    // recorded as detail (std::source_location).

    /// Add a filter or Valve, by value: add_filter(Validate{}).
    template <typename F>
    Pipeline& add_filter(F filter, std::source_location at = std::source_location::current()) {
        static_assert(std::is_base_of_v<IFilter, F>,
                      "codeupipe: add_filter takes a filter by value, a struct deriving IFilter "
                      "(not a unique_ptr, not a lambda): the type is the step's identity");
        std::string base;
        if constexpr (std::is_same_v<F, Valve>) base = filter.inner_identity();
        else base = detail::identity_of<F>();
        steps_.push_back(Step{identity(std::move(base), at), FilterStep{std::make_unique<F>(std::move(filter))}});
        return *this;
    }

    /// Add a tap, by value: add_tap(Audit{}).
    template <typename T>
    Pipeline& add_tap(T tap, std::source_location at = std::source_location::current()) {
        static_assert(std::is_base_of_v<ITap, T>,
                      "codeupipe: add_tap takes a tap by value, a struct deriving ITap (not a unique_ptr, "
                      "not a lambda): the type is the step's identity");
        steps_.push_back(Step{identity(detail::identity_of<T>(), at), TapStep{std::make_unique<T>(std::move(tap))}});
        return *this;
    }

    /// Nest a named Pipeline subclass; it is one step in this pipeline's State.
    template <typename P>
    Pipeline& add_pipeline(P child, std::source_location at = std::source_location::current()) {
        static_assert(std::is_base_of_v<Pipeline, P>, "codeupipe: add_pipeline takes a Pipeline subclass");
        static_assert(!std::is_same_v<P, Pipeline>,
                      "codeupipe: a nested pipeline must be a named Pipeline subclass "
                      "(struct Onboarding : cup::Pipeline {...}), identified like a filter");
        steps_.push_back(Step{identity(detail::identity_of<P>(), at),
                              NestedStep{std::make_unique<P>(std::move(child))}});
        return *this;
    }

    /// Each step's identity, in order.
    std::vector<std::string> identities() const {
        std::vector<std::string> out;
        out.reserve(steps_.size());
        for (const auto& s : steps_) out.push_back(s.name);
        return out;
    }

    /// identity -> "file:line" of the add call (detail, not identity).
    const std::map<std::string, std::string>& step_sites() const noexcept { return step_sites_; }
    Pipeline& use_hook(std::unique_ptr<IHook> h) {
        hooks_.push_back(std::move(h));
        return *this;
    }
    Pipeline& observe_timing(bool on = true) noexcept {
        observe_timing_ = on;
        return *this;
    }

    std::size_t  step_count() const noexcept { return steps_.size(); }
    const State& state() const noexcept { return state_; }

    Payload run(Payload payload) {
        state_.reset();
        if (hooks_.empty()) {  // hot path: no hook bookkeeping at all
            for (auto& step : steps_) run_step(step, payload);
            return payload;
        }
        // Pipeline-level events use an empty step name and wrap the step-level
        // ones; on a failure the failing step's on_error (in run_step) is
        // followed by the pipeline's. Same contract in every runtime.
        static const std::string pipeline_level{};
        for (auto& h : hooks_) h->before(pipeline_level, payload);
        try {
            for (auto& step : steps_) run_step(step, payload);
        } catch (const std::exception& e) {
            for (auto& h : hooks_) h->on_error(pipeline_level, e, payload);
            throw;
        }
        for (auto& h : hooks_) h->after(pipeline_level, payload);
        return payload;
    }

private:
    struct FilterStep { std::unique_ptr<IFilter> f; };
    struct TapStep    { std::unique_ptr<ITap> t; };
    struct NestedStep { std::unique_ptr<Pipeline> p; };
    struct Step {
        std::string                                     name;  // the step's identity
        std::variant<FilterStep, TapStep, NestedStep>   kind;
    };

    std::string identity(std::string base, const std::source_location& at) {
        const auto n = ++occurrences_[base];
        std::string id = n == 1 ? std::move(base) : base + "#" + std::to_string(n);
        std::string file = at.file_name();
        const auto slash = file.find_last_of("/\\");
        step_sites_[id] = (slash == std::string::npos ? file : file.substr(slash + 1)) + ":" + std::to_string(at.line());
        return id;
    }

    void run_step(Step& step, Payload& payload) {
        if (auto* tap = std::get_if<TapStep>(&step.kind)) {
            // Plane B: a Tap failure never halts the pipeline. It is recorded
            // under the Tap's name; hooks are not notified.
            try {
                tap->t->observe(payload);
            } catch (const std::exception& e) {
                state_.record_error(step.name, std::current_exception(), e.what());
            } catch (...) {
                state_.record_error(step.name, std::current_exception(), "unknown error");
            }
            state_.mark_executed(step.name);
            return;
        }

        for (auto& h : hooks_) h->before(step.name, payload);
        const auto t0 = observe_timing_ ? std::chrono::steady_clock::now()
                                        : std::chrono::steady_clock::time_point{};
        try {
            if (auto* f = std::get_if<FilterStep>(&step.kind)) {
                payload = f->f->call(payload);
                if (f->f->last_skipped()) state_.mark_skipped(step.name);
                else                      state_.mark_executed(step.name);
            } else {
                payload = std::get<NestedStep>(step.kind).p->run(payload);
                state_.mark_executed(step.name);
            }
        } catch (const std::exception& e) {
            if (observe_timing_) state_.record_timing(step.name, seconds_since(t0));
            for (auto& h : hooks_) h->on_error(step.name, e, payload);
            throw;
        }
        if (observe_timing_) state_.record_timing(step.name, seconds_since(t0));
        for (auto& h : hooks_) h->after(step.name, payload);
    }

    static double seconds_since(std::chrono::steady_clock::time_point t0) {
        return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    }

    std::vector<Step>                    steps_{};
    std::vector<std::unique_ptr<IHook>>  hooks_{};
    State                                state_{};
    bool                                 observe_timing_ = false;
    std::map<std::string, int>           occurrences_{};
    std::map<std::string, std::string>   step_sites_{};
};

} // namespace cup
