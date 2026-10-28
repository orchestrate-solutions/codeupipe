use std::cell::{Cell, RefCell};
use std::collections::HashMap;
use std::fmt;
use std::rc::Rc;
use std::time::Instant;

use crate::filter::Filter;
use crate::hook::Hook;
use crate::named_pipeline::NamedPipeline;
use crate::payload::Payload;
use crate::pipeline_data::PipelineData;
use crate::predicate::Predicate;
use crate::state::State;
use crate::step_error::StepError;
use crate::step_label::label_of;
use crate::tap::Tap;
use crate::valve::Valve;

/// A step that Hooks see: it runs, and its failure stops the run.
enum Gated<P> {
    Filter(Box<dyn Filter<P>>),
    Valve(Valve<P>),
    Pipeline(Box<Pipeline<P>>),
}

enum Step<P> {
    Tap(Box<dyn Tap<P>>),
    Gated(Gated<P>),
}

struct Labeled<P> {
    label: String,
    step: Step<P>,
}

/// Pipeline: runs the steps in order.
///
/// Filters change the Payload, Valves gate a Filter, Taps read, Hooks see the
/// lifecycle, and State records what ran. Add steps with `add_filter`,
/// `add_valve`, `add_tap` and `add_pipeline`, add Hooks with `use_hook`, and
/// run with `pipeline.run(&payload)`.
///
/// It carries a `Payload` unless you give it a type of your own
/// (`Pipeline<Order>`, see `PipelineData`).
pub struct Pipeline<P = Payload> {
    label: String,
    steps: Vec<Labeled<P>>,
    uses: HashMap<String, usize>,
    hooks: Vec<Box<dyn Hook<P>>>,
    runs: Runs,
    timing: bool,
    lineage: bool,
}

/// The runs of a pipeline. Each run writes into a State of its own; this
/// keeps the State of the run that started last, for `state()`.
#[derive(Default)]
struct Runs {
    /// The number of runs that have started; a run's number is its ticket.
    started: Cell<u64>,
    /// The State of the run that started last, and that has ended.
    last: RefCell<Rc<State>>,
    /// A State that no run and no reader has, kept for its storage.
    spare: RefCell<Option<State>>,
}

// cup: allow-plain a primitive itself: the framework makes the primitives, so it is not written with them
impl Runs {
    fn start(&self) -> u64 {
        let ticket = self.started.get() + 1;
        self.started.set(ticket);
        ticket
    }

    /// A State for a run, with the storage of an earlier one when there is one.
    fn new_state(&self) -> State {
        let mut state = self.spare.take().unwrap_or_default();
        state.reset();
        state
    }

    /// Keep `state` as the State of the pipeline, unless a run that started
    /// later has ended already (a run inside this run).
    fn end(&self, ticket: u64, state: State) {
        if ticket != self.started.get() {
            self.spare.replace(Some(state));
            return;
        }
        let earlier = self.last.replace(Rc::new(state));
        if let Ok(earlier) = Rc::try_unwrap(earlier) {
            self.spare.replace(Some(earlier));
        }
    }
}

impl<P: PipelineData> Default for Pipeline<P> {
    fn default() -> Self {
        Pipeline::new()
    }
}

impl<P> fmt::Debug for Pipeline<P> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Pipeline")
            .field("label", &self.label)
            .field("steps", &self.labels())
            .finish()
    }
}

impl<P> Pipeline<P> {
    /// The label of each step, in order.
    pub fn labels(&self) -> Vec<String> {
        self.steps.iter().map(|step| step.label.clone()).collect()
    }
}

// cup: allow-plain a primitive itself: the framework makes the primitives, so it is not written with them
impl<P: PipelineData> Pipeline<P> {
    /// A pipeline with no name. Nested, its label is `Pipeline`.
    pub fn new() -> Self {
        Pipeline {
            label: "Pipeline".to_string(),
            steps: Vec::new(),
            uses: HashMap::new(),
            hooks: Vec::new(),
            runs: Runs::default(),
            timing: false,
            lineage: false,
        }
    }

    /// The pipeline that `named` adds the steps of. Its label is the name of
    /// the type of `named`.
    pub fn named<N: NamedPipeline<P>>(named: N) -> Self {
        let mut pipeline = Pipeline::new();
        pipeline.label = label_of::<N>();
        named.add_steps(&mut pipeline);
        pipeline
    }

    /// The State of the run that started last, once it has ended.
    ///
    /// A State belongs to one run, and this is for a caller with one run at a
    /// time. It is a snapshot: a later run does not change it. A caller with
    /// more than one run at a time gives each run its own State
    /// (`run_with_state`).
    pub fn state(&self) -> Rc<State> {
        Rc::clone(&self.runs.last.borrow())
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

    fn push(&mut self, base: String, step: Step<P>) {
        let label = self.next_label(base);
        self.steps.push(Labeled { label, step });
    }

    /// Add a Filter.
    pub fn add_filter<F: Filter<P> + 'static>(&mut self, filter: F) {
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
    pub fn add_valve<Q: Predicate<P> + 'static, F: Filter<P> + 'static>(
        &mut self,
        predicate: Q,
        filter: F,
    ) {
        let valve = Valve {
            predicate: Box::new(predicate),
            filter: Box::new(filter),
        };
        self.push(label_of::<F>(), Step::Gated(Gated::Valve(valve)));
    }

    /// Add a Tap.
    pub fn add_tap<T: Tap<P> + 'static>(&mut self, tap: T) {
        self.push(label_of::<T>(), Step::Tap(Box::new(tap)));
    }

    /// Nest a Pipeline as one step of this Pipeline.
    pub fn add_pipeline(&mut self, pipeline: Pipeline<P>) {
        self.push(
            pipeline.label.clone(),
            Step::Gated(Gated::Pipeline(Box::new(pipeline))),
        );
    }

    /// Add a Hook.
    pub fn use_hook<H: Hook<P> + 'static>(&mut self, hook: H) {
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
    /// The run writes into a new State, which `state()` gives afterwards.
    ///
    /// It takes `&self`: a step can hold the pipeline that it is in (an `Rc`)
    /// and run it again, and each run has its own State.
    pub fn run(&self, input: &P) -> Result<P, StepError> {
        let ticket = self.runs.start();
        let mut state = self.runs.new_state();
        let mut payload = input.clone(); // the caller's value is not changed
        let result = self.run_steps(&mut payload, &mut state);
        self.runs.end(ticket, state);
        result.map(|()| payload)
    }

    /// `run`, writing into `state`, which the caller gives. A caller with more
    /// than one run at a time gives each run its own State.
    pub fn run_with_state(&self, input: &P, state: &mut State) -> Result<P, StepError> {
        let ticket = self.runs.start();
        let mut payload = input.clone(); // the caller's value is not changed
        let result = self.run_steps(&mut payload, state);
        self.runs.end(ticket, state.clone());
        result.map(|()| payload)
    }

    fn run_steps(&self, payload: &mut P, state: &mut State) -> Result<(), StepError> {
        let Pipeline {
            steps,
            hooks,
            timing,
            lineage,
            ..
        } = self;

        for hook in hooks.iter() {
            hook.before(None, payload);
        }

        for Labeled { label, step } in steps.iter() {
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
// cup: allow-plain a primitive itself: the framework makes the primitives, so it is not written with them
fn run_gated<P: PipelineData>(gated: &Gated<P>, payload: &mut P) -> Result<bool, StepError> {
    match gated {
        Gated::Filter(filter) => filter.call(payload).map(|()| true),
        Gated::Valve(valve) if !valve.predicate.test(payload) => Ok(false),
        Gated::Valve(valve) => valve.filter.call(payload).map(|()| true),
        Gated::Pipeline(inner) => {
            // A run of its own, with its own State: a failure inside leaves this
            // Payload as it was.
            *payload = inner.run(payload)?;
            Ok(true)
        }
    }
}
