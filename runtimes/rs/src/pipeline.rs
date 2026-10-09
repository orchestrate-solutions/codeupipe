//! Pipeline: The Orchestrator
//!
//! Runs filters in sequence with hooks, taps, and state tracking.
//! Supports batch (.run) and streaming (.stream) execution modes.
//!
//! This is a synchronous Rust port. The Python version is async;
//! here we use synchronous trait methods. For async Rust, wrap with
//! tokio or async-std in your application layer.
//!
//! See also: TypeScript, Python, Go, C# implementations.

use crate::filter::Filter;
use crate::hook::Hook;
use crate::payload::Payload;
use crate::state::State;
use crate::stream_filter::StreamFilter;
use crate::tap::Tap;
use crate::typed::{TypedError, TypedFilter, TypedTap};

use std::time::Instant;

// ---------------------------------------------------------------------------
// Filter/Tap → Typed adapters
//
// The dynamic Pipeline stores filters and taps as their Typed equivalents.
// Adapters wrap the trait objects once at add_* time; per-hop cost is one
// extra vtable dispatch (measured — see bench_hop_matrix).
// ---------------------------------------------------------------------------

struct FilterAdapter(Box<dyn Filter>);
impl TypedFilter<Payload> for FilterAdapter {
    fn call(&self, ctx: Payload) -> Result<Payload, TypedError> {
        self.0.call(ctx)
    }
    fn last_skipped(&self) -> bool {
        Filter::last_skipped(&*self.0)
    }
}

struct TapAdapter(Box<dyn Tap>);
impl TypedTap<Payload> for TapAdapter {
    fn observe(&self, ctx: &Payload) {
        self.0.observe(ctx);
    }
}


/// Run a Tap on Plane B: a Tap failure never halts the pipeline. Rust Taps
/// fail by panicking (`observe` returns nothing), so the panic is caught and
/// returned as the message to record in `state.errors`. Same contract in
/// every runtime (conformance/cases/tap.json). Needs `panic = "unwind"`
/// (the default; wasm32 aborts on panic, so there it cannot be contained).
fn observe_contained(tap: &dyn TypedTap<Payload>, payload: &Payload) -> Option<String> {
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| tap.observe(payload)))
        .err()
        .map(|panic| {
            panic
                .downcast_ref::<String>()
                .cloned()
                .or_else(|| panic.downcast_ref::<&str>().map(|s| (*s).to_string()))
                .unwrap_or_else(|| "tap panicked".to_string())
        })
}

// ---------------------------------------------------------------------------
// Step types
// ---------------------------------------------------------------------------

enum StepKind {
    FilterStep(Box<dyn TypedFilter<Payload>>),
    StreamFilterStep(Box<dyn StreamFilter>),
    TapStep(Box<dyn TypedTap<Payload>>),
    ParallelStep(Vec<Box<dyn Filter>>),
    PipelineStep(Pipeline),
}

struct Step {
    /// The step's identity (conformance/API.md, "Step identity").
    name: String,
    kind: StepKind,
}

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------

/// Orchestrator — runs filters in sequence with hooks, taps, and state
/// tracking.
pub struct Pipeline {
    steps: Vec<Step>,
    hooks: Vec<Box<dyn Hook>>,
    state: State,
    observe_timing: bool,
    observe_state: bool,
    observe_lineage: bool,
    disabled_taps: Vec<String>,
    occurrences: std::collections::HashMap<String, usize>,
    step_sites: std::collections::HashMap<String, String>,
}

impl Pipeline {
    /// Each step's identity, in order.
    pub fn identities(&self) -> Vec<String> {
        self.steps.iter().map(|s| s.name.clone()).collect()
    }

    /// identity -> `file:line` of the add call (detail, not identity).
    pub fn step_sites(&self) -> &std::collections::HashMap<String, String> {
        &self.step_sites
    }

    /// Number a base identity from its second use; record where it was added.
    fn identity(&mut self, base: String, at: &std::panic::Location<'_>) -> String {
        let n = self.occurrences.entry(base.clone()).or_insert(0);
        *n += 1;
        let id = if *n == 1 { base } else { format!("{base}#{n}") };
        self.step_sites.insert(id.clone(), crate::step_identity::site(at));
        id
    }

    /// Create a new empty pipeline.
    pub fn new() -> Self {
        Pipeline {
            steps: Vec::new(),
            hooks: Vec::new(),
            state: State::new(),
            observe_timing: false,
            observe_state: true,
            observe_lineage: false,
            disabled_taps: Vec::new(),
            occurrences: std::collections::HashMap::new(),
            step_sites: std::collections::HashMap::new(),
        }
    }

    /// Access pipeline execution state after run().
    pub fn state(&self) -> &State {
        &self.state
    }

    /// Add a filter (or Valve), identified by its type path.
    #[track_caller]
    pub fn add_filter<F: Filter + 'static>(mut self, filter: F) -> Self {
        let at = std::panic::Location::caller();
        let base = match (&filter as &dyn std::any::Any).downcast_ref::<crate::valve::Valve>() {
            Some(valve) => valve.inner_identity().to_string(),
            None => crate::step_identity::identify::<F>("Filter"),
        };
        let name = self.identity(base, at);
        self.steps.push(Step {
            name,
            kind: StepKind::FilterStep(Box::new(FilterAdapter(Box::new(filter)))),
        });
        self
    }

    /// Add a stream filter, identified by its type path.
    #[track_caller]
    pub fn add_stream_filter<S: StreamFilter + 'static>(mut self, filter: S) -> Self {
        let at = std::panic::Location::caller();
        let name = self.identity(crate::step_identity::identify::<S>("StreamFilter"), at);
        self.steps.push(Step {
            name,
            kind: StepKind::StreamFilterStep(Box::new(filter)),
        });
        self
    }

    /// Add a tap (observation point), identified by its type path.
    #[track_caller]
    pub fn add_tap<T: Tap + 'static>(mut self, tap: T) -> Self {
        let at = std::panic::Location::caller();
        let name = self.identity(crate::step_identity::identify::<T>("Tap"), at);
        self.steps.push(Step {
            name,
            kind: StepKind::TapStep(Box::new(TapAdapter(Box::new(tap)))),
        });
        self
    }

    /// Attach a lifecycle hook.
    pub fn use_hook(mut self, hook: Box<dyn Hook>) -> Self {
        self.hooks.push(hook);
        self
    }

    /// Add a parallel fan-out/fan-in group: `parallel[<member identities>]`.
    #[track_caller]
    pub fn add_parallel(mut self, group: crate::parallel::Parallel) -> Self {
        let at = std::panic::Location::caller();
        let name = self.identity(format!("parallel[{}]", group.members.join(",")), at);
        self.steps.push(Step {
            name,
            kind: StepKind::ParallelStep(group.filters),
        });
        self
    }

    /// Nest a named pipeline type as a single step (see [`crate::Nestable`]).
    #[track_caller]
    pub fn add_pipeline<P: crate::nestable::Nestable>(mut self, nested: P) -> Self {
        let at = std::panic::Location::caller();
        let name = self.identity(crate::step_identity::identify::<P>("Nested pipeline"), at);
        self.steps.push(Step {
            name,
            kind: StepKind::PipelineStep(nested.into_pipeline()),
        });
        self
    }

    /// Enable observation features.
    pub fn observe(mut self, timing: bool, lineage: bool) -> Self {
        self.observe_timing = timing;
        self.observe_lineage = lineage;
        self
    }

    /// Enable or disable state recording (executed/skipped/chunks/timings).
    pub fn observe_state(mut self, state: bool) -> Self {
        self.observe_state = state;
        self
    }

    /// Disable specific taps, by identity.
    pub fn disable_taps(mut self, names: &[&str]) -> Self {
        for n in names {
            self.disabled_taps.push(n.to_string());
        }
        self
    }

    // ------------------------------------------------------------------
    // Batch execution
    // ------------------------------------------------------------------

    /// True when the common case can bypass hooks, timing, lineage, and taps.
    fn can_run_fast(&self) -> bool {
        self.hooks.is_empty()
            && !self.observe_timing
            && !self.observe_lineage
            && self.disabled_taps.is_empty()
            && !self.steps.iter().any(|s| matches!(
                s.kind,
                StepKind::TapStep(_) | StepKind::PipelineStep(_) | StepKind::StreamFilterStep(_)
            ))
    }

    /// Hot path — no hooks, no timing, no lineage, no taps, no nested pipelines.
    /// Filter and parallel steps only. Bypasses per-hop clones and Instant reads.
    fn run_fast(
        &mut self,
        initial_payload: Payload,
    ) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
        self.state = State::new();
        self.reserve_state_capacity();
        let mut payload = initial_payload;
        let observe_state = self.observe_state;

        for step in &self.steps {
            match &step.kind {
                StepKind::FilterStep(filter) => {
                    payload = filter.call(payload)?;
                    if observe_state {
                        if filter.last_skipped() {
                            self.state.mark_skipped(&step.name);
                        } else {
                            self.state.mark_executed(&step.name);
                        }
                    }
                }
                StepKind::ParallelStep(filters) => {
                    let mut merged = payload.clone();
                    for filter in filters {
                        let result = filter.call(payload.clone())?;
                        merged = merged.merge(&result);
                    }
                    payload = merged;
                    if observe_state {
                        self.state.mark_executed(&step.name);
                    }
                }
                // can_run_fast excluded the rest.
                _ => unreachable!("can_run_fast guarantees filter/parallel only"),
            }
        }

        Ok(payload)
    }

    /// Execute the pipeline — flow payload through all filters and taps.
    pub fn run(
        &mut self,
        initial_payload: Payload,
    ) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
        // Reject StreamFilters in batch mode
        for step in &self.steps {
            if matches!(step.kind, StepKind::StreamFilterStep(_)) {
                return Err(format!(
                    "Pipeline contains StreamFilter '{}'. Use pipeline.stream() instead.",
                    step.name
                )
                .into());
            }
        }

        if self.can_run_fast() {
            return self.run_fast(initial_payload);
        }

        self.state = State::new();
        self.reserve_state_capacity();
        let mut payload = initial_payload;

        // Hook: pipeline start
        for hook in &self.hooks {
            hook.before(None, &payload);
        }

        let step_count = self.steps.len();
        for i in 0..step_count {
            let step_name = self.steps[i].name.clone();
            let t0 = Instant::now();

            // A nested Pipeline needs `&mut` to run, which the shared borrow in
            // the match below cannot give, so it is handled first.
            if matches!(self.steps[i].kind, StepKind::PipelineStep(_)) {
                for hook in &self.hooks {
                    hook.before(Some(&step_name), &payload);
                }
                let result = match &mut self.steps[i].kind {
                    StepKind::PipelineStep(child) => child.run(payload.clone()),
                    _ => unreachable!(),
                };
                match result {
                    Ok(out) => payload = out,
                    Err(e) => {
                        self.fire_error(&step_name, &*e, &payload);
                        return Err(e);
                    }
                }
                if self.observe_state {
                    self.state.mark_executed(&step_name);
                    if self.observe_timing {
                        self.state.record_timing(&step_name, t0.elapsed().as_secs_f64());
                    }
                }
                if self.observe_lineage {
                    payload = payload.stamp(&step_name);
                }
                for hook in &self.hooks {
                    hook.after(Some(&step_name), &payload);
                }
                continue;
            }

            match &self.steps[i].kind {
                StepKind::TapStep(tap) => {
                    if self.disabled_taps.contains(&step_name) {
                        if self.observe_state {
                            self.state.mark_skipped(&step_name);
                        }
                        continue;
                    }
                    let failure = observe_contained(tap.as_ref(), &payload);
                    if self.observe_state {
                        self.state.mark_executed(&step_name);
                        if let Some(message) = failure {
                            self.state.record_error(&step_name, &message);
                        }
                    }
                    continue; // no timing for taps
                }

                StepKind::FilterStep(filter) => {
                    for hook in &self.hooks {
                        hook.before(Some(&step_name), &payload);
                    }

                    let payload_for_error = payload.clone();
                    match filter.call(payload) {
                        Ok(result) => {
                            payload = result;
                            if self.observe_state {
                                if filter.last_skipped() {
                                    self.state.mark_skipped(&step_name);
                                } else {
                                    self.state.mark_executed(&step_name);
                                }
                            }
                        }
                        Err(e) => {
                            let duration = t0.elapsed().as_secs_f64();
                            if self.observe_timing {
                                if self.observe_state && self.observe_timing {
                                    self.state.record_timing(&step_name, duration);
                                }
                            }
                            self.fire_error(&step_name, &*e, &payload_for_error);
                            return Err(e);
                        }
                    }

                    for hook in &self.hooks {
                        hook.after(Some(&step_name), &payload);
                    }
                }

                StepKind::ParallelStep(filters) => {
                    // Sequential execution (true parallelism needs threads/rayon)
                    let mut merged = payload.clone();
                    for filter in filters {
                        match filter.call(payload.clone()) {
                            Ok(result) => merged = merged.merge(&result),
                            Err(e) => {
                                self.fire_error(&step_name, &*e, &payload);
                                return Err(e);
                            }
                        }
                    }
                    payload = merged;
                    if self.observe_state {
                        self.state.mark_executed(&step_name);
                    }
                }

                StepKind::PipelineStep(_) => {
                    unreachable!("nested pipelines are handled before this match");
                }

                StepKind::StreamFilterStep(_) => {
                    unreachable!("StreamFilters rejected above");
                }
            }

            // Post-step timing
            let duration = t0.elapsed().as_secs_f64();
            if self.observe_timing {
                if self.observe_state && self.observe_timing {
                    self.state.record_timing(&step_name, duration);
                }
            }
            if self.observe_lineage {
                payload = payload.stamp(&step_name);
            }
        }

        // Hook: pipeline end
        for hook in &self.hooks {
            hook.after(None, &payload);
        }

        Ok(payload)
    }

    /// Notify hooks of a failed step: `on_error` for the failing step, then
    /// for the pipeline (`None`), mirroring before/after, which fire at both
    /// levels. Same contract in every runtime (conformance/cases/hook.json).
    fn fire_error(&self, step: &str, error: &(dyn std::error::Error + Send + Sync), payload: &Payload) {
        for hook in &self.hooks {
            hook.on_error(Some(step), error, payload);
        }
        for hook in &self.hooks {
            hook.on_error(None, error, payload);
        }
    }

    // ------------------------------------------------------------------
    // Streaming execution
    // ------------------------------------------------------------------

    /// Stream payloads through the pipeline.
    ///
    /// Takes an iterator of payloads and returns a Vec of results.
    /// (Rust doesn't have async generators; for true streaming, use
    /// channels or async-stream in your application layer.)
    pub fn stream(
        &mut self,
        source: Vec<Payload>,
    ) -> Result<Vec<Payload>, Box<dyn std::error::Error + Send + Sync>> {
        self.state = State::new();
        self.reserve_state_capacity();

        let sentinel = Payload::new();
        for hook in &self.hooks {
            hook.before(None, &sentinel);
        }

        let mut current = source;

        for i in 0..self.steps.len() {
            let step_name = self.steps[i].name.clone();
            let mut next = Vec::new();

            match &self.steps[i].kind {
                StepKind::TapStep(tap) => {
                    if self.disabled_taps.contains(&step_name) {
                        if self.observe_state {
                            self.state.mark_skipped(&step_name);
                        }
                        next = current;
                    } else {
                        if self.observe_state {
                            self.state.mark_executed(&step_name);
                        }
                        for chunk in &current {
                            let failure = observe_contained(tap.as_ref(), chunk);
                            if self.observe_state {
                                self.state.increment_chunks(&step_name, 1);
                                if let Some(message) = failure {
                                    self.state.record_error(&step_name, &message);
                                }
                            }
                        }
                        next = current;
                    }
                }

                StepKind::StreamFilterStep(sf) => {
                    if self.observe_state {
                        self.state.mark_executed(&step_name);
                    }
                    for chunk in current {
                        let results = sf.stream(chunk)?;
                        for r in results {
                            if self.observe_state {
                                self.state.increment_chunks(&step_name, 1);
                            }
                            next.push(r);
                        }
                    }
                }

                StepKind::FilterStep(filter) => {
                    if self.observe_state {
                        self.state.mark_executed(&step_name);
                    }
                    for chunk in current {
                        let result = filter.call(chunk)?;
                        if self.observe_state {
                            self.state.increment_chunks(&step_name, 1);
                        }
                        next.push(result);
                    }
                }

                StepKind::ParallelStep(filters) => {
                    if self.observe_state {
                        self.state.mark_executed(&step_name);
                    }
                    for chunk in current {
                        let mut merged = chunk.clone();
                        for filter in filters {
                            let result = filter.call(chunk.clone())?;
                            merged = merged.merge(&result);
                        }
                        if self.observe_state {
                            self.state.increment_chunks(&step_name, 1);
                        }
                        next.push(merged);
                    }
                }

                StepKind::PipelineStep(_) => {
                    return Err("Nested pipeline in stream mode not yet supported".into());
                }
            }

            current = next;
        }

        for hook in &self.hooks {
            hook.after(None, &sentinel);
        }

        Ok(current)
    }

    // ------------------------------------------------------------------
    // Introspection
    // ------------------------------------------------------------------

    fn reserve_state_capacity(&mut self) {
        if !self.observe_state {
            return;
        }
        let step_capacity = self.steps.len();
        self.state.executed.reserve(step_capacity);
        self.state.skipped.reserve(step_capacity);
        self.state.errors.reserve(step_capacity);
        self.state.chunks_processed.reserve(step_capacity);
        self.state.timings.reserve(step_capacity);
    }

    /// Return step count.
    pub fn step_count(&self) -> usize {
        self.steps.len()
    }

    /// Return step names and types.
    pub fn describe(&self) -> Vec<(String, String)> {
        self.steps
            .iter()
            .map(|s| {
                let kind = match &s.kind {
                    StepKind::FilterStep(_) => "filter",
                    StepKind::StreamFilterStep(_) => "stream_filter",
                    StepKind::TapStep(_) => "tap",
                    StepKind::ParallelStep(_) => "parallel",
                    StepKind::PipelineStep(_) => "pipeline",
                };
                (s.name.clone(), kind.to_string())
            })
            .collect()
    }
}

impl Default for Pipeline {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use crate::parallel::Parallel;
    use super::*;
    use crate::payload::Value;
    use std::sync::{Arc, Mutex};

    // Test filter: adds 1 to "x"
    struct AddOne;
    impl Filter for AddOne {
        fn call(
            &self,
            payload: Payload,
        ) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
            let x = payload.get("x").and_then(|v| v.as_int()).unwrap_or(0);
            Ok(payload.insert("x", Value::Int(x + 1)))
        }
    }

    // Test filter: multiplies "x" by 2
    struct MultiplyTwo;
    impl Filter for MultiplyTwo {
        fn call(
            &self,
            payload: Payload,
        ) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
            let x = payload.get("x").and_then(|v| v.as_int()).unwrap_or(0);
            Ok(payload.insert("x", Value::Int(x * 2)))
        }
    }

    // Test filter: sets a key
    struct SetKey {
        key: String,
        value: Value,
    }
    impl SetKey {
        fn new(key: &str, value: Value) -> Self {
            SetKey {
                key: key.to_string(),
                value,
            }
        }
    }
    impl Filter for SetKey {
        fn call(
            &self,
            payload: Payload,
        ) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
            Ok(payload.insert(&self.key, self.value.clone()))
        }
    }

    // Test filter: always fails
    struct FailFilter;
    impl Filter for FailFilter {
        fn call(
            &self,
            _payload: Payload,
        ) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>> {
            Err("intentional failure".into())
        }
    }

    // Test stream filter: splits text into words
    struct SplitChunks;
    impl StreamFilter for SplitChunks {
        fn stream(
            &self,
            chunk: Payload,
        ) -> Result<Vec<Payload>, Box<dyn std::error::Error + Send + Sync>> {
            let text = chunk.get("text").and_then(|v| v.as_str()).unwrap_or("");
            let results: Vec<Payload> = text
                .split_whitespace()
                .map(|word| chunk.insert("word", Value::Str(word.to_string())))
                .collect();
            Ok(results)
        }
    }

    // Test stream filter: drops everything
    struct DropFilter;
    impl StreamFilter for DropFilter {
        fn stream(
            &self,
            _chunk: Payload,
        ) -> Result<Vec<Payload>, Box<dyn std::error::Error + Send + Sync>> {
            Ok(Vec::new())
        }
    }

    // Test tap: records payloads
    struct RecordingTap {
        observed: Arc<Mutex<Vec<String>>>,
    }
    impl RecordingTap {
        fn new() -> (Self, Arc<Mutex<Vec<String>>>) {
            let observed = Arc::new(Mutex::new(Vec::new()));
            (
                RecordingTap {
                    observed: observed.clone(),
                },
                observed,
            )
        }
    }
    impl Tap for RecordingTap {
        fn observe(&self, payload: &Payload) {
            let mut obs = self.observed.lock().unwrap();
            obs.push(format!("{}", payload));
        }
    }

    // Test hook: records calls
    struct RecordingHook {
        calls: Arc<Mutex<Vec<String>>>,
    }
    impl RecordingHook {
        fn new() -> (Self, Arc<Mutex<Vec<String>>>) {
            let calls = Arc::new(Mutex::new(Vec::new()));
            (
                RecordingHook {
                    calls: calls.clone(),
                },
                calls,
            )
        }
    }
    impl Hook for RecordingHook {
        fn before(&self, filter_name: Option<&str>, _payload: &Payload) {
            let mut c = self.calls.lock().unwrap();
            c.push(format!("before:{}", filter_name.unwrap_or("pipeline")));
        }
        fn after(&self, filter_name: Option<&str>, _payload: &Payload) {
            let mut c = self.calls.lock().unwrap();
            c.push(format!("after:{}", filter_name.unwrap_or("pipeline")));
        }
        fn on_error(
            &self,
            _filter_name: Option<&str>,
            error: &(dyn std::error::Error + Send + Sync),
            _payload: &Payload,
        ) {
            let mut c = self.calls.lock().unwrap();
            c.push(format!("error:{}", error));
        }
    }

    // --- Batch tests ---

    #[test]
    fn empty_pipeline() {
        let mut p = Pipeline::new();
        let result = p.run(Payload::new().insert("x", Value::Int(1))).unwrap();
        assert_eq!(result.get("x").unwrap().as_int(), Some(1));
    }

    #[test]
    fn single_filter() {
        let mut p = Pipeline::new().add_filter(AddOne);
        let result = p.run(Payload::new().insert("x", Value::Int(0))).unwrap();
        assert_eq!(result.get("x").unwrap().as_int(), Some(1));
        assert_eq!(p.state().executed, vec!["codeupipe_core::pipeline::tests::AddOne"]);
    }

    #[test]
    fn multiple_filters() {
        let mut p = Pipeline::new()
            .add_filter(AddOne)
            .add_filter(MultiplyTwo);
        let result = p.run(Payload::new().insert("x", Value::Int(5))).unwrap();
        // (5 + 1) * 2 = 12
        assert_eq!(result.get("x").unwrap().as_int(), Some(12));
        assert_eq!(p.state().executed, vec!["codeupipe_core::pipeline::tests::AddOne", "codeupipe_core::pipeline::tests::MultiplyTwo"]);
    }

    #[test]
    fn tap_observes() {
        let (tap, observed) = RecordingTap::new();
        let mut p = Pipeline::new()
            .add_filter(AddOne)
            .add_tap(tap);
        p.run(Payload::new().insert("x", Value::Int(0))).unwrap();
        assert_eq!(observed.lock().unwrap().len(), 1);
        assert_eq!(p.state().executed, vec!["codeupipe_core::pipeline::tests::AddOne", "codeupipe_core::pipeline::tests::RecordingTap"]);
    }

    #[test]
    fn disabled_tap() {
        let (tap, observed) = RecordingTap::new();
        let mut p = Pipeline::new()
            .add_tap(tap)
            .disable_taps(&["codeupipe_core::pipeline::tests::RecordingTap"]);
        p.run(Payload::new()).unwrap();
        assert!(observed.lock().unwrap().is_empty());
        assert_eq!(p.state().skipped, vec!["codeupipe_core::pipeline::tests::RecordingTap"]);
    }

    #[test]
    fn hooks_fire() {
        let (hook, calls) = RecordingHook::new();
        let mut p = Pipeline::new()
            .add_filter(AddOne)
            .use_hook(Box::new(hook));
        p.run(Payload::new().insert("x", Value::Int(0))).unwrap();
        let c = calls.lock().unwrap();
        assert_eq!(
            *c,
            vec![
                "before:pipeline",
                "before:codeupipe_core::pipeline::tests::AddOne",
                "after:codeupipe_core::pipeline::tests::AddOne",
                "after:pipeline"
            ]
        );
    }

    #[test]
    fn hooks_on_error() {
        let (hook, calls) = RecordingHook::new();
        let mut p = Pipeline::new()
            .add_filter(FailFilter)
            .use_hook(Box::new(hook));
        let result = p.run(Payload::new());
        assert!(result.is_err());
        let c = calls.lock().unwrap();
        assert!(c.iter().any(|s| s.starts_with("error:")));
    }

    #[test]
    fn parallel_execution() {
        let mut p = Pipeline::new().add_parallel(Parallel::new().with(SetKey::new("a", Value::Int(1))).with(SetKey::new("b", Value::Int(2))));
        let result = p.run(Payload::new()).unwrap();
        assert_eq!(result.get("a").unwrap().as_int(), Some(1));
        assert_eq!(result.get("b").unwrap().as_int(), Some(2));
        assert_eq!(p.state().executed, vec!["parallel[codeupipe_core::pipeline::tests::SetKey,codeupipe_core::pipeline::tests::SetKey]"]);
    }

    #[test]
    fn observe_timing() {
        let mut p = Pipeline::new()
            .add_filter(AddOne)
            .observe(true, false);
        p.run(Payload::new().insert("x", Value::Int(0))).unwrap();
        assert!(p.state().timings.contains_key("codeupipe_core::pipeline::tests::AddOne"));
    }

    #[test]
    fn observe_lineage() {
        let mut p = Pipeline::new()
            .add_filter(AddOne)
            .add_filter(MultiplyTwo)
            .observe(false, true);
        let result = p.run(Payload::new().insert("x", Value::Int(0))).unwrap();
        assert_eq!(result.lineage(), &["codeupipe_core::pipeline::tests::AddOne", "codeupipe_core::pipeline::tests::MultiplyTwo"]);
    }

    #[test]
    fn rejects_stream_filter_in_batch() {
        let mut p = Pipeline::new().add_stream_filter(SplitChunks);
        let result = p.run(Payload::new().insert("text", Value::Str("a b".to_string())));
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("StreamFilter"));
    }

    #[test]
    fn state_resets_between_runs() {
        let mut p = Pipeline::new().add_filter(AddOne);
        p.run(Payload::new().insert("x", Value::Int(0))).unwrap();
        assert_eq!(p.state().executed, vec!["codeupipe_core::pipeline::tests::AddOne"]);
        p.run(Payload::new().insert("x", Value::Int(10))).unwrap();
        assert_eq!(p.state().executed, vec!["codeupipe_core::pipeline::tests::AddOne"]);
    }

    #[test]
    fn describe_pipeline() {
        let p = Pipeline::new()
            .add_filter(AddOne)
            .add_tap(RecordingTap::new().0);
        let desc = p.describe();
        assert_eq!(desc.len(), 2);
        assert_eq!(desc[0], ("codeupipe_core::pipeline::tests::AddOne".to_string(), "filter".to_string()));
        assert_eq!(desc[1], ("codeupipe_core::pipeline::tests::RecordingTap".to_string(), "tap".to_string()));
    }

    #[test]
    fn step_count() {
        let p = Pipeline::new()
            .add_filter(AddOne)
            .add_filter(MultiplyTwo);
        assert_eq!(p.step_count(), 2);
    }

    // --- Streaming tests ---

    #[test]
    fn stream_regular_filter() {
        let mut p = Pipeline::new().add_filter(AddOne);
        let source = vec![
            Payload::new().insert("x", Value::Int(1)),
            Payload::new().insert("x", Value::Int(2)),
            Payload::new().insert("x", Value::Int(3)),
        ];
        let results = p.stream(source).unwrap();
        let xs: Vec<i64> = results
            .iter()
            .map(|r| r.get("x").unwrap().as_int().unwrap())
            .collect();
        assert_eq!(xs, vec![2, 3, 4]);
        assert_eq!(p.state().chunks_processed["codeupipe_core::pipeline::tests::AddOne"], 3);
    }

    #[test]
    fn stream_fan_out() {
        let mut p = Pipeline::new().add_stream_filter(SplitChunks);
        let source = vec![Payload::new().insert("text", Value::Str("hello world".to_string()))];
        let results = p.stream(source).unwrap();
        let words: Vec<&str> = results
            .iter()
            .map(|r| r.get("word").unwrap().as_str().unwrap())
            .collect();
        assert_eq!(words, vec!["hello", "world"]);
    }

    #[test]
    fn stream_drop_filter() {
        let mut p = Pipeline::new().add_stream_filter(DropFilter);
        let source = vec![
            Payload::new().insert("x", Value::Int(1)),
            Payload::new().insert("x", Value::Int(2)),
        ];
        let results = p.stream(source).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn stream_tap_observes() {
        let (tap, observed) = RecordingTap::new();
        let mut p = Pipeline::new().add_tap(tap);
        let source = vec![
            Payload::new().insert("x", Value::Int(1)),
            Payload::new().insert("x", Value::Int(2)),
        ];
        let results = p.stream(source).unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(observed.lock().unwrap().len(), 2);
        assert_eq!(p.state().chunks_processed["codeupipe_core::pipeline::tests::RecordingTap"], 2);
    }

    #[test]
    fn stream_disabled_tap() {
        let (tap, observed) = RecordingTap::new();
        let mut p = Pipeline::new()
            .add_tap(tap)
            .disable_taps(&["codeupipe_core::pipeline::tests::RecordingTap"]);
        let source = vec![Payload::new()];
        let results = p.stream(source).unwrap();
        assert_eq!(results.len(), 1);
        assert!(observed.lock().unwrap().is_empty());
        assert_eq!(p.state().skipped, vec!["codeupipe_core::pipeline::tests::RecordingTap"]);
    }

    #[test]
    fn stream_hooks_fire() {
        let (hook, calls) = RecordingHook::new();
        let mut p = Pipeline::new()
            .add_filter(AddOne)
            .use_hook(Box::new(hook));
        let source = vec![Payload::new().insert("x", Value::Int(0))];
        p.stream(source).unwrap();
        let c = calls.lock().unwrap();
        assert!(c.contains(&"before:pipeline".to_string()));
        assert!(c.contains(&"after:pipeline".to_string()));
    }

    #[test]
    fn stream_parallel() {
        let mut p = Pipeline::new().add_parallel(Parallel::new().with(SetKey::new("a", Value::Int(1))).with(SetKey::new("b", Value::Int(2))));
        let source = vec![Payload::new(), Payload::new()];
        let results = p.stream(source).unwrap();
        assert_eq!(results.len(), 2);
        for r in &results {
            assert_eq!(r.get("a").unwrap().as_int(), Some(1));
            assert_eq!(r.get("b").unwrap().as_int(), Some(2));
        }
    }

    // --- Fluent builder ---

    #[test]
    fn fluent_builder() {
        let p = Pipeline::new()
            .add_filter(AddOne)
            .add_filter(MultiplyTwo)
            .add_tap(RecordingTap::new().0)
            .observe(true, false);
        assert_eq!(p.step_count(), 3);
    }
}
