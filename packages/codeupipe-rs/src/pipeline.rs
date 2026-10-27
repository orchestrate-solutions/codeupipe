use std::collections::HashMap;
use std::fmt;
use std::time::Instant;

use crate::filter::Filter;
use crate::hook::Hook;
use crate::named_pipeline::NamedPipeline;
use crate::payload::Payload;
use crate::predicate::Predicate;
use crate::state::State;
use crate::step_error::StepError;
use crate::step_label::label_of;
use crate::tap::Tap;
use crate::valve::Valve;

/// A step that Hooks see: it runs, and its failure stops the run.
enum Gated {
    Filter(Box<dyn Filter>),
    Valve(Valve),
    Pipeline(Box<Pipeline>),
}

enum Step {
    Tap(Box<dyn Tap>),
    Gated(Gated),
}

struct Labeled {
    label: String,
    step: Step,
}

/// Pipeline: runs the steps in order.
///
/// Filters change the Payload, Valves gate a Filter, Taps read, Hooks see the
/// lifecycle, and State records what ran. Add steps with `add_filter`,
/// `add_valve`, `add_tap` and `add_pipeline`, add Hooks with `use_hook`, and
/// run with `pipeline.run(&payload)`.
pub struct Pipeline {
    label: String,
    steps: Vec<Labeled>,
    uses: HashMap<String, usize>,
    hooks: Vec<Box<dyn Hook>>,
    state: State,
    timing: bool,
    lineage: bool,
}

impl Default for Pipeline {
    fn default() -> Self {
        Pipeline::new()
    }
}

impl fmt::Debug for Pipeline {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Pipeline")
            .field("label", &self.label)
            .field("steps", &self.labels())
            .finish()
    }
}

impl Pipeline {
    /// A pipeline with no name. Nested, its label is `Pipeline`.
    pub fn new() -> Self {
        Pipeline {
            label: "Pipeline".to_string(),
            steps: Vec::new(),
            uses: HashMap::new(),
            hooks: Vec::new(),
            state: State::default(),
            timing: false,
            lineage: false,
        }
    }

    /// The pipeline that `named` adds the steps of. Its label is the name of
    /// the type of `named`.
    pub fn named<N: NamedPipeline>(named: N) -> Self {
        let mut pipeline = Pipeline::new();
        pipeline.label = label_of::<N>();
        named.add_steps(&mut pipeline);
        pipeline
    }

    /// What happened in the last run.
    pub fn state(&self) -> &State {
        &self.state
    }

    /// The label of each step, in order.
    pub fn labels(&self) -> Vec<String> {
        self.steps.iter().map(|step| step.label.clone()).collect()
    }

    /// The type name of the step, with a number from its second use in this pipeline.
    fn next_label(&mut self, base: String) -> String {
        let count = self.uses.entry(base.clone()).or_insert(0);
        *count += 1;
        if *count == 1 {
            base
        } else {
            format!("{base}#{count}")
        }
    }

    fn push(&mut self, base: String, step: Step) {
        let label = self.next_label(base);
        self.steps.push(Labeled { label, step });
    }

    /// Add a Filter.
    pub fn add_filter<F: Filter + 'static>(&mut self, filter: F) {
        self.push(
            label_of::<F>(),
            Step::Gated(Gated::Filter(Box::new(filter))),
        );
    }

    /// Add a Valve: `filter` runs only when `predicate.test(payload)` is true.
    ///
    /// The condition comes first, then the Filter that it controls. When the
    /// test is false the Payload passes through unchanged and the step is
    /// recorded as skipped. The step has the label of its Filter.
    pub fn add_valve<P: Predicate + 'static, F: Filter + 'static>(
        &mut self,
        predicate: P,
        filter: F,
    ) {
        let valve = Valve {
            predicate: Box::new(predicate),
            filter: Box::new(filter),
        };
        self.push(label_of::<F>(), Step::Gated(Gated::Valve(valve)));
    }

    /// Add a Tap.
    pub fn add_tap<T: Tap + 'static>(&mut self, tap: T) {
        self.push(label_of::<T>(), Step::Tap(Box::new(tap)));
    }

    /// Nest a Pipeline as one step of this Pipeline.
    pub fn add_pipeline(&mut self, pipeline: Pipeline) {
        self.push(
            pipeline.label.clone(),
            Step::Gated(Gated::Pipeline(Box::new(pipeline))),
        );
    }

    /// Add a Hook.
    pub fn use_hook<H: Hook + 'static>(&mut self, hook: H) {
        self.hooks.push(Box::new(hook));
    }

    /// Turn timing (the time of each step, in State) and lineage (labels on
    /// the Payload) on or off. Both are off by default.
    pub fn observe(&mut self, timing: bool, lineage: bool) {
        self.timing = timing;
        self.lineage = lineage;
    }

    /// Run the steps in order on a copy of `input`, and return the result.
    ///
    /// A Filter failure stops the run and is returned after the Hooks have
    /// seen it. A Tap failure is recorded in State and the run continues.
    pub fn run(&mut self, input: &Payload) -> Result<Payload, StepError> {
        let mut payload = input.copy(); // the caller's Payload is not changed
        self.run_on(&mut payload)?;
        Ok(payload)
    }

    fn run_on(&mut self, payload: &mut Payload) -> Result<(), StepError> {
        self.state = State::default();
        let Pipeline {
            steps,
            hooks,
            state,
            timing,
            lineage,
            ..
        } = self;

        for hook in hooks.iter() {
            hook.before(None, payload);
        }

        for Labeled { label, step } in steps.iter_mut() {
            let gated = match step {
                Step::Tap(tap) => {
                    if let Err(error) = tap.observe(payload) {
                        state.record_error(label, error);
                    }
                    state.mark_executed(label);
                    continue;
                }
                Step::Gated(gated) => gated,
            };

            let started = if *timing { Some(Instant::now()) } else { None };
            for hook in hooks.iter() {
                hook.before(Some(label), payload);
            }

            match run_gated(gated, payload) {
                Ok(true) => state.mark_executed(label),
                Ok(false) => state.mark_skipped(label),
                Err(error) => {
                    if let Some(started) = started {
                        state.record_timing(label, started.elapsed());
                    }
                    // The failing step first, then the pipeline: on_error
                    // fires at both levels, as before and after do.
                    for hook in hooks.iter() {
                        hook.on_error(Some(label), &error, payload);
                    }
                    for hook in hooks.iter() {
                        hook.on_error(None, &error, payload);
                    }
                    return Err(error);
                }
            }

            for hook in hooks.iter() {
                hook.after(Some(label), payload);
            }
            if let Some(started) = started {
                state.record_timing(label, started.elapsed());
            }
            if *lineage {
                payload.stamp(label);
            }
        }

        for hook in hooks.iter() {
            hook.after(None, payload);
        }
        Ok(())
    }
}

/// Run one step that Hooks see. `Ok(false)` is a Valve that skipped its Filter.
fn run_gated(gated: &mut Gated, payload: &mut Payload) -> Result<bool, StepError> {
    match gated {
        Gated::Filter(filter) => filter.call(payload).map(|()| true),
        Gated::Valve(valve) if !valve.predicate.test(payload) => Ok(false),
        Gated::Valve(valve) => valve.filter.call(payload).map(|()| true),
        Gated::Pipeline(inner) => {
            // As a run of its own: a failure inside leaves this Payload as it was.
            let mut result = payload.copy();
            inner.run_on(&mut result)?;
            *payload = result;
            Ok(true)
        }
    }
}
