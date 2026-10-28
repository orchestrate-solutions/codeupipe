// A State belongs to one run, not to the Pipeline (conformance/API.md,
// "State"): the caller can give the State, each run writes into its own, a
// step can run its own pipeline again while it runs, and state() is the
// State of the run that started last.
use std::cell::RefCell;
use std::rc::{Rc, Weak};

use codeupipe::{Filter, Map, Payload, Pipeline, Predicate, State, StepError, Tap, Value};

struct SetFilter;

impl Filter for SetFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert("a", 1);
        Ok(())
    }
}

struct IsInnerPredicate;

impl Predicate for IsInnerPredicate {
    fn test(&self, payload: &Payload) -> bool {
        payload.get("inner") == Some(&Value::Bool(true))
    }
}

struct MarkFilter;

impl Filter for MarkFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert("gated", true);
        Ok(())
    }
}

struct FailTap;

impl Tap for FailTap {
    fn observe(&self, _payload: &Payload) -> Result<(), StepError> {
        Err("sink down".into())
    }
}

/// Runs the pipeline that it is in one more time, with `inner` set, and a
/// State of its own. The pipeline is given to it after it is made.
#[derive(Clone, Default)]
struct RunAgainFilter {
    pipeline: Rc<RefCell<Weak<Pipeline>>>,
    inner_states: Rc<RefCell<Vec<State>>>,
}

impl Filter for RunAgainFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        if payload.get("inner") == Some(&Value::Bool(true)) {
            return Ok(());
        }
        let pipeline = self
            .pipeline
            .borrow()
            .upgrade()
            .expect("the pipeline is there");
        let mut state = State::new();
        pipeline.run_with_state(&Payload::from_map(Map::from([("inner", true)])), &mut state)?;
        self.inner_states.borrow_mut().push(state);
        Ok(())
    }
}

/// first, again (a run inside the run), gate (only for the inner run).
fn pipeline_that_runs_again() -> (Rc<Pipeline>, RunAgainFilter) {
    let again = RunAgainFilter::default();
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(SetFilter);
    pipeline.add_filter(again.clone());
    pipeline.add_valve(IsInnerPredicate, MarkFilter);
    let pipeline = Rc::new(pipeline);
    *again.pipeline.borrow_mut() = Rc::downgrade(&pipeline);
    (pipeline, again)
}

#[test]
fn the_caller_gives_the_state_of_a_run() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(SetFilter);
    pipeline.add_valve(IsInnerPredicate, MarkFilter);
    pipeline.add_tap(FailTap);
    let mut state = State::new();
    let out = pipeline
        .run_with_state(&Payload::new(), &mut state)
        .unwrap();
    assert_eq!(out.get("a"), Some(&Value::from(1)));
    assert_eq!(state.executed(), ["SetFilter", "FailTap"]);
    assert_eq!(state.skipped(), ["MarkFilter"]);
    assert_eq!(state.errors()[0].1.to_string(), "sink down");
    // It is also the State of the run that started last.
    assert_eq!(pipeline.state().executed(), state.executed());
    assert_eq!(pipeline.state().errors()[0].1.to_string(), "sink down");
}

#[test]
fn a_run_that_starts_inside_another_run_has_its_own_state() {
    let (pipeline, again) = pipeline_that_runs_again();
    let mut outer = State::new();
    pipeline
        .run_with_state(&Payload::new(), &mut outer)
        .unwrap();
    assert_eq!(outer.executed(), ["SetFilter", "RunAgainFilter"]);
    assert_eq!(outer.skipped(), ["MarkFilter"]);
    let inner = again.inner_states.borrow();
    assert_eq!(inner.len(), 1);
    assert_eq!(
        inner[0].executed(),
        ["SetFilter", "RunAgainFilter", "MarkFilter"]
    );
    assert!(inner[0].skipped().is_empty());
}

#[test]
fn with_no_state_from_the_caller_the_pipeline_has_the_state_of_the_run_that_started_last() {
    let (pipeline, _again) = pipeline_that_runs_again();
    pipeline.run(&Payload::new()).unwrap();
    // The inner run started last, inside the outer one.
    assert_eq!(
        pipeline.state().executed(),
        ["SetFilter", "RunAgainFilter", "MarkFilter"]
    );
}

#[test]
fn a_state_that_was_read_does_not_change_with_the_next_run() {
    let mut pipeline = Pipeline::new();
    pipeline.add_valve(IsInnerPredicate, MarkFilter);
    pipeline
        .run(&Payload::from_map(Map::from([("inner", true)])))
        .unwrap();
    let first = pipeline.state();
    pipeline.run(&Payload::new()).unwrap();
    assert_eq!(first.executed(), ["MarkFilter"]);
    assert_eq!(pipeline.state().skipped(), ["MarkFilter"]);
}

struct FailFilter;
impl Filter for FailFilter {
    fn call(&self, _payload: &mut Payload) -> Result<(), StepError> {
        Err("boom".into())
    }
}

#[test]
fn a_failed_run_with_the_callers_state_keeps_the_steps_before_the_failure() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(SetFilter);
    pipeline.add_filter(FailFilter);
    let mut state = State::new();
    assert!(pipeline
        .run_with_state(&Payload::new(), &mut state)
        .is_err());
    assert_eq!(state.executed(), ["SetFilter"]);
    assert_eq!(pipeline.state().executed(), ["SetFilter"]);
}
