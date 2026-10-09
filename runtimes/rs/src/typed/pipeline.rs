//! TypedPipeline<Ctx> — the orchestrator for typed payloads.
//!
//! Same shape as `Pipeline`: filters, taps, valves, hooks, and State.
//! Ctx flows through unchanged in type; only its data mutates.
//!
//! Hot path bypasses hooks/taps/state when none are configured — same
//! technique as the dynamic Pipeline's `run_fast`.

use super::{TypedError, TypedFilter, TypedHook, TypedTap};
use crate::state::State;
use std::time::Instant;

enum TypedStep<Ctx> {
    FilterStep(Box<dyn TypedFilter<Ctx>>),
    TapStep(Box<dyn TypedTap<Ctx>>),
}

struct StepEntry<Ctx> {
    name: String,
    kind: TypedStep<Ctx>,
}

/// A pipeline over a compile-time-known `Ctx` type.
pub struct TypedPipeline<Ctx> {
    steps: Vec<StepEntry<Ctx>>,
    hooks: Vec<Box<dyn TypedHook<Ctx>>>,
    state: State,
    observe_timing: bool,
    observe_state: bool,
    disabled_taps: Vec<String>,
}

impl<Ctx> TypedPipeline<Ctx> {
    pub fn new() -> Self {
        Self {
            steps: Vec::new(),
            hooks: Vec::new(),
            state: State::new(),
            observe_timing: false,
            observe_state: true,
            disabled_taps: Vec::new(),
        }
    }

    pub fn state(&self) -> &State {
        &self.state
    }

    pub fn add_filter<F>(mut self, filter: F, name: &str) -> Self
    where
        F: TypedFilter<Ctx> + 'static,
    {
        self.steps.push(StepEntry {
            name: name.to_string(),
            kind: TypedStep::FilterStep(Box::new(filter)),
        });
        self
    }

    pub fn add_boxed_filter(mut self, filter: Box<dyn TypedFilter<Ctx>>, name: &str) -> Self {
        self.steps.push(StepEntry {
            name: name.to_string(),
            kind: TypedStep::FilterStep(filter),
        });
        self
    }

    pub fn add_tap<T>(mut self, tap: T, name: &str) -> Self
    where
        T: TypedTap<Ctx> + 'static,
    {
        self.steps.push(StepEntry {
            name: name.to_string(),
            kind: TypedStep::TapStep(Box::new(tap)),
        });
        self
    }

    pub fn use_hook<H>(mut self, hook: H) -> Self
    where
        H: TypedHook<Ctx> + 'static,
    {
        self.hooks.push(Box::new(hook));
        self
    }

    pub fn observe(mut self, timing: bool) -> Self {
        self.observe_timing = timing;
        self
    }

    pub fn observe_state(mut self, enabled: bool) -> Self {
        self.observe_state = enabled;
        self
    }

    pub fn disable_taps(mut self, names: &[&str]) -> Self {
        for n in names {
            self.disabled_taps.push(n.to_string());
        }
        self
    }

    pub fn step_count(&self) -> usize {
        self.steps.len()
    }

    pub fn describe(&self) -> Vec<(String, &'static str)> {
        self.steps
            .iter()
            .map(|s| {
                let kind = match &s.kind {
                    TypedStep::FilterStep(_) => "filter",
                    TypedStep::TapStep(_) => "tap",
                };
                (s.name.clone(), kind)
            })
            .collect()
    }

    // ------------------------------------------------------------------
    // Execution
    // ------------------------------------------------------------------

    fn can_run_fast(&self) -> bool {
        self.hooks.is_empty()
            && !self.observe_timing
            && self.disabled_taps.is_empty()
            && !self.steps.iter().any(|s| matches!(s.kind, TypedStep::TapStep(_)))
    }

    fn reserve_state_capacity(&mut self) {
        if !self.observe_state {
            return;
        }
        let cap = self.steps.len();
        self.state.executed.reserve(cap);
        self.state.skipped.reserve(cap);
        self.state.errors.reserve(cap);
        self.state.timings.reserve(cap);
    }

    fn run_fast(&mut self, initial: Ctx) -> Result<Ctx, TypedError> {
        self.state = State::new();
        self.reserve_state_capacity();
        let observe_state = self.observe_state;
        let mut ctx = initial;
        for step in &self.steps {
            match &step.kind {
                TypedStep::FilterStep(filter) => {
                    ctx = filter.call(ctx)?;
                    if observe_state {
                        self.state.mark_executed(&step.name);
                    }
                }
                TypedStep::TapStep(_) => unreachable!("can_run_fast excluded taps"),
            }
        }
        Ok(ctx)
    }

    /// Execute the pipeline. Flows Ctx through every step.
    pub fn run(&mut self, initial: Ctx) -> Result<Ctx, TypedError> {
        if self.can_run_fast() {
            return self.run_fast(initial);
        }

        self.state = State::new();
        self.reserve_state_capacity();
        let mut ctx = initial;

        for hook in &self.hooks {
            hook.before(None, &ctx);
        }

        for step in &self.steps {
            let t0 = if self.observe_timing { Some(Instant::now()) } else { None };

            match &step.kind {
                TypedStep::TapStep(tap) => {
                    if self.disabled_taps.contains(&step.name) {
                        if self.observe_state {
                            self.state.mark_skipped(&step.name);
                        }
                        continue;
                    }
                    tap.observe(&ctx);
                    if self.observe_state {
                        self.state.mark_executed(&step.name);
                    }
                    continue;
                }

                TypedStep::FilterStep(filter) => {
                    for hook in &self.hooks {
                        hook.before(Some(&step.name), &ctx);
                    }

                    match filter.call(ctx) {
                        Ok(next) => {
                            ctx = next;
                            if self.observe_state {
                                self.state.mark_executed(&step.name);
                            }
                        }
                        Err(e) => {
                            let err_msg = e.to_string();
                            // Ctx was consumed by filter.call — TypedHook::on_error
                            // intentionally takes no ctx. Use a Tap upstream to snapshot
                            // if you need pre-error state.
                            for hook in &self.hooks {
                                hook.on_error(Some(&step.name), &err_msg);
                            }
                            return Err(e);
                        }
                    }

                    for hook in &self.hooks {
                        hook.after(Some(&step.name), &ctx);
                    }
                }
            }

            if let Some(t0) = t0 {
                let duration = t0.elapsed().as_secs_f64();
                if self.observe_state {
                    self.state.record_timing(&step.name, duration);
                }
            }
        }

        for hook in &self.hooks {
            hook.after(None, &ctx);
        }

        Ok(ctx)
    }
}

impl<Ctx> Default for TypedPipeline<Ctx> {
    fn default() -> Self {
        Self::new()
    }
}


#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;

    #[derive(Clone, Debug, PartialEq)]
    struct Ctx {
        n: i64,
        flag: bool,
    }

    struct Increment;
    impl TypedFilter<Ctx> for Increment {
        fn call(&self, mut ctx: Ctx) -> Result<Ctx, TypedError> {
            ctx.n += 1;
            Ok(ctx)
        }
    }

    struct Doubler;
    impl TypedFilter<Ctx> for Doubler {
        fn call(&self, mut ctx: Ctx) -> Result<Ctx, TypedError> {
            ctx.n *= 2;
            Ok(ctx)
        }
    }

    struct RecordingTap {
        seen: Arc<AtomicUsize>,
    }
    impl TypedTap<Ctx> for RecordingTap {
        fn observe(&self, ctx: &Ctx) {
            self.seen.store(ctx.n as usize, Ordering::Relaxed);
        }
    }

    #[test]
    fn empty_pipeline_passes_ctx_through() {
        let mut pipe: TypedPipeline<Ctx> = TypedPipeline::new();
        let out = pipe.run(Ctx { n: 42, flag: false }).unwrap();
        assert_eq!(out.n, 42);
    }

    #[test]
    fn single_filter_transforms() {
        let mut pipe = TypedPipeline::new().add_filter(Increment, "inc");
        let out = pipe.run(Ctx { n: 0, flag: false }).unwrap();
        assert_eq!(out.n, 1);
    }

    #[test]
    fn chained_filters_apply_in_order() {
        let mut pipe = TypedPipeline::new()
            .add_filter(Increment, "inc")
            .add_filter(Doubler, "dbl");
        let out = pipe.run(Ctx { n: 3, flag: false }).unwrap();
        // (3 + 1) * 2 = 8
        assert_eq!(out.n, 8);
    }

    #[test]
    fn tap_observes_without_mutating() {
        let seen = Arc::new(AtomicUsize::new(0));
        let mut pipe = TypedPipeline::new()
            .add_filter(Increment, "inc")
            .add_tap(RecordingTap { seen: seen.clone() }, "peek");
        let out = pipe.run(Ctx { n: 10, flag: false }).unwrap();
        assert_eq!(out.n, 11);
        assert_eq!(seen.load(Ordering::Relaxed), 11);
    }

    #[test]
    fn disabled_tap_marks_skipped() {
        let seen = Arc::new(AtomicUsize::new(0));
        let mut pipe = TypedPipeline::new()
            .add_tap(RecordingTap { seen: seen.clone() }, "peek")
            .disable_taps(&["peek"]);
        let out = pipe.run(Ctx { n: 5, flag: false }).unwrap();
        assert_eq!(out.n, 5);
        assert_eq!(seen.load(Ordering::Relaxed), 0);
        assert!(pipe.state().skipped.iter().any(|s| s == "peek"));
    }

    #[test]
    fn valve_runs_when_predicate_true() {
        use super::super::TypedValve;
        let valve = TypedValve::new(Increment, |c: &Ctx| c.flag);
        let mut pipe = TypedPipeline::new().add_filter(valve, "gated_inc");
        let out = pipe.run(Ctx { n: 5, flag: true }).unwrap();
        assert_eq!(out.n, 6);
    }

    #[test]
    fn valve_skips_when_predicate_false() {
        use super::super::TypedValve;
        let valve = TypedValve::new(Increment, |c: &Ctx| c.flag);
        let mut pipe = TypedPipeline::new().add_filter(valve, "gated_inc");
        let out = pipe.run(Ctx { n: 5, flag: false }).unwrap();
        assert_eq!(out.n, 5); // unchanged
    }

    struct Counter {
        before: Arc<AtomicUsize>,
        after: Arc<AtomicUsize>,
    }
    impl TypedHook<Ctx> for Counter {
        fn before(&self, step: Option<&str>, _ctx: &Ctx) {
            if step.is_some() {
                self.before.fetch_add(1, Ordering::Relaxed);
            }
        }
        fn after(&self, step: Option<&str>, _ctx: &Ctx) {
            if step.is_some() {
                self.after.fetch_add(1, Ordering::Relaxed);
            }
        }
    }

    #[test]
    fn hooks_fire_for_each_filter_step() {
        let before = Arc::new(AtomicUsize::new(0));
        let after = Arc::new(AtomicUsize::new(0));
        let mut pipe = TypedPipeline::new()
            .add_filter(Increment, "inc")
            .add_filter(Doubler, "dbl")
            .use_hook(Counter { before: before.clone(), after: after.clone() });
        let out = pipe.run(Ctx { n: 1, flag: false }).unwrap();
        assert_eq!(out.n, 4);
        assert_eq!(before.load(Ordering::Relaxed), 2);
        assert_eq!(after.load(Ordering::Relaxed), 2);
    }

    #[test]
    fn removing_taps_yields_identical_output() {
        // Manifesto invariant #1: removing taps must not change output.
        let seen = Arc::new(AtomicUsize::new(0));
        let mut with_tap = TypedPipeline::new()
            .add_filter(Increment, "inc")
            .add_tap(RecordingTap { seen: seen.clone() }, "peek")
            .add_filter(Doubler, "dbl");
        let mut without_tap = TypedPipeline::new()
            .add_filter(Increment, "inc")
            .add_filter(Doubler, "dbl");
        let a = with_tap.run(Ctx { n: 3, flag: false }).unwrap();
        let b = without_tap.run(Ctx { n: 3, flag: false }).unwrap();
        assert_eq!(a, b);
    }

    #[test]
    fn same_ctx_same_pipe_same_output() {
        // Manifesto invariant #2: determinism.
        let mut pipe = TypedPipeline::new()
            .add_filter(Increment, "inc")
            .add_filter(Doubler, "dbl");
        let a = pipe.run(Ctx { n: 7, flag: false }).unwrap();
        let mut pipe2 = TypedPipeline::new()
            .add_filter(Increment, "inc")
            .add_filter(Doubler, "dbl");
        let b = pipe2.run(Ctx { n: 7, flag: false }).unwrap();
        assert_eq!(a, b);
    }
}
