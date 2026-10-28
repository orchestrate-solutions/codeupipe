use std::cell::RefCell;
use std::rc::Rc;

use codeupipe::{
    Filter, Hook, Map, NamedPipeline, Payload, Pipeline, Predicate, StepError, Tap, Value,
};

fn n(payload: &Payload) -> f64 {
    payload.get("n").and_then(Value::as_f64).unwrap_or(0.0)
}

struct AddFilter;

impl Filter for AddFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert("n", n(payload) + 1.0);
        Ok(())
    }
}

struct AddOtherFilter;

impl Filter for AddOtherFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert("n", n(payload) + 1.0);
        Ok(())
    }
}

struct FailFilter;

impl Filter for FailFilter {
    fn call(&self, _payload: &mut Payload) -> Result<(), StepError> {
        Err("boom".into())
    }
}

/// Writes, then fails: a Hook sees the Payload as the step left it.
struct HalfDoneFilter;

impl Filter for HalfDoneFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert("half", true);
        Err("stopped half way".into())
    }
}

struct IsOnPredicate;

impl Predicate for IsOnPredicate {
    fn test(&self, payload: &Payload) -> bool {
        payload.get("on") == Some(&Value::Bool(true))
    }
}

struct SeeTap {
    seen: Rc<RefCell<Vec<Option<Value>>>>,
}

impl Tap for SeeTap {
    fn observe(&self, payload: &Payload) -> Result<(), StepError> {
        self.seen.borrow_mut().push(payload.get("n").cloned());
        Ok(())
    }
}

struct FailTap;

impl Tap for FailTap {
    fn observe(&self, _payload: &Payload) -> Result<(), StepError> {
        Err("sink is down".into())
    }
}

struct FailOtherTap;

impl Tap for FailOtherTap {
    fn observe(&self, _payload: &Payload) -> Result<(), StepError> {
        Err("sink is down again".into())
    }
}

struct InnerPipeline;

impl NamedPipeline for InnerPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_filter(AddFilter);
        pipeline.add_filter(AddFilter);
    }
}

#[derive(Clone, Default)]
struct RecordHook {
    events: Rc<RefCell<Vec<String>>>,
}

impl RecordHook {
    fn events(&self) -> Vec<String> {
        self.events.borrow().clone()
    }
}

impl Hook for RecordHook {
    fn before(&self, step: Option<&str>, _payload: &Payload) {
        self.events
            .borrow_mut()
            .push(format!("before:{}", step.unwrap_or("")));
    }
    fn after(&self, step: Option<&str>, _payload: &Payload) {
        self.events
            .borrow_mut()
            .push(format!("after:{}", step.unwrap_or("")));
    }
    fn on_error(&self, step: Option<&str>, _error: &StepError, _payload: &Payload) {
        self.events
            .borrow_mut()
            .push(format!("error:{}", step.unwrap_or("")));
    }
}

fn labels_of_errors(pipeline: &Pipeline) -> Vec<String> {
    pipeline
        .state()
        .errors()
        .iter()
        .map(|(label, _)| label.clone())
        .collect()
}

#[test]
fn an_empty_pipeline_returns_the_data_it_was_given() {
    let out = Pipeline::new()
        .run(&Payload::from_map(Map::from([("a", 1)])))
        .unwrap();
    assert_eq!(out.to_dict(), Map::from([("a", 1)]));
}

#[test]
fn steps_run_in_order_and_state_records_them() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_filter(AddOtherFilter);
    let out = pipeline.run(&Payload::new()).unwrap();
    assert_eq!(n(&out), 2.0);
    assert_eq!(pipeline.state().executed(), ["AddFilter", "AddOtherFilter"]);
    assert!(pipeline.state().skipped().is_empty());
    assert!(pipeline.state().errors().is_empty());
}

#[test]
fn run_works_on_a_copy_so_the_callers_payload_is_not_changed() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    let given = Payload::from_map(Map::from([("n", 1)]));
    let out = pipeline.run(&given).unwrap();
    assert_eq!(n(&given), 1.0);
    assert_eq!(n(&out), 2.0);
}

#[test]
fn a_valve_runs_its_filter_when_the_predicate_is_true() {
    let mut pipeline = Pipeline::new();
    pipeline.add_valve(IsOnPredicate, AddFilter);
    let out = pipeline
        .run(&Payload::from_map(Map::from([("on", true)])))
        .unwrap();
    assert_eq!(n(&out), 1.0);
    assert_eq!(pipeline.state().executed(), ["AddFilter"]);
    assert!(pipeline.state().skipped().is_empty());
}

#[test]
fn a_valve_skips_its_filter_when_the_predicate_is_false() {
    let mut pipeline = Pipeline::new();
    pipeline.add_valve(IsOnPredicate, AddFilter);
    let out = pipeline
        .run(&Payload::from_map(Map::from([("on", false)])))
        .unwrap();
    assert!(!out.has("n"));
    assert!(pipeline.state().executed().is_empty());
    assert_eq!(pipeline.state().skipped(), ["AddFilter"]);
}

#[test]
fn a_filter_failure_stops_the_run_and_state_keeps_the_steps_before_it() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_filter(FailFilter);
    pipeline.add_filter(AddFilter);
    let error = pipeline.run(&Payload::new()).unwrap_err();
    assert_eq!(error.to_string(), "boom");
    assert_eq!(pipeline.state().executed(), ["AddFilter"]);
}

#[test]
fn a_tap_reads_the_payload_and_counts_as_executed() {
    let seen = Rc::new(RefCell::new(Vec::new()));
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_tap(SeeTap { seen: seen.clone() });
    pipeline.run(&Payload::new()).unwrap();
    assert_eq!(*seen.borrow(), [Some(Value::from(1))]);
    assert_eq!(pipeline.state().executed(), ["AddFilter", "SeeTap"]);
}

#[test]
fn a_tap_failure_is_recorded_and_does_not_stop_the_run() {
    let hook = RecordHook::default();
    let mut pipeline = Pipeline::new();
    pipeline.add_tap(FailTap);
    pipeline.add_tap(FailOtherTap);
    pipeline.add_filter(AddFilter);
    pipeline.use_hook(hook.clone());
    let out = pipeline.run(&Payload::new()).unwrap();
    assert_eq!(n(&out), 1.0);
    assert_eq!(
        pipeline.state().executed(),
        ["FailTap", "FailOtherTap", "AddFilter"]
    );
    assert_eq!(labels_of_errors(&pipeline), ["FailTap", "FailOtherTap"]);
    assert_eq!(pipeline.state().errors()[0].1.to_string(), "sink is down");
    assert_eq!(
        hook.events(),
        ["before:", "before:AddFilter", "after:AddFilter", "after:"]
    );
}

#[test]
fn a_nested_pipeline_is_one_step() {
    let mut pipeline = Pipeline::new();
    pipeline.add_pipeline(Pipeline::named(InnerPipeline));
    pipeline.add_filter(AddFilter);
    let out = pipeline.run(&Payload::new()).unwrap();
    assert_eq!(n(&out), 3.0);
    assert_eq!(pipeline.state().executed(), ["InnerPipeline", "AddFilter"]);
}

#[test]
fn hooks_see_the_pipeline_and_each_filter_or_valve_in_order() {
    let hook = RecordHook::default();
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_valve(IsOnPredicate, AddOtherFilter);
    pipeline.add_tap(SeeTap {
        seen: Rc::default(),
    });
    pipeline.use_hook(hook.clone());
    pipeline.run(&Payload::new()).unwrap();
    assert_eq!(
        hook.events(),
        [
            "before:",
            "before:AddFilter",
            "after:AddFilter",
            "before:AddOtherFilter",
            "after:AddOtherFilter",
            "after:"
        ]
    );
}

#[test]
fn on_a_filter_failure_a_hook_gets_the_step_then_the_pipeline_and_no_after() {
    let hook = RecordHook::default();
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_filter(FailFilter);
    pipeline.use_hook(hook.clone());
    assert!(pipeline.run(&Payload::new()).is_err());
    assert_eq!(
        hook.events(),
        [
            "before:",
            "before:AddFilter",
            "after:AddFilter",
            "before:FailFilter",
            "error:FailFilter",
            "error:"
        ]
    );
}

#[test]
fn a_hook_gets_the_error_itself() {
    #[derive(Clone, Default)]
    struct KeepErrorHook {
        seen: Rc<RefCell<Vec<usize>>>,
    }
    impl Hook for KeepErrorHook {
        fn on_error(&self, _step: Option<&str>, error: &StepError, _payload: &Payload) {
            self.seen.borrow_mut().push(address(error));
        }
    }
    fn address(error: &StepError) -> usize {
        &**error as *const (dyn std::error::Error + Send + Sync) as *const () as usize
    }

    let hook = KeepErrorHook::default();
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(FailFilter);
    pipeline.use_hook(hook.clone());
    let error = pipeline.run(&Payload::new()).unwrap_err();
    // Both calls get the error that run returns: the same value, not a copy.
    assert_eq!(*hook.seen.borrow(), [address(&error), address(&error)]);
}

#[test]
fn on_error_gets_the_payload_as_the_failing_step_left_it() {
    #[derive(Clone, Default)]
    struct KeepPayloadHook {
        seen: Rc<RefCell<Vec<Map>>>,
    }
    impl Hook for KeepPayloadHook {
        fn on_error(&self, _step: Option<&str>, _error: &StepError, payload: &Payload) {
            self.seen.borrow_mut().push(payload.to_dict());
        }
    }

    let hook = KeepPayloadHook::default();
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_filter(HalfDoneFilter);
    pipeline.use_hook(hook.clone());
    assert!(pipeline.run(&Payload::new()).is_err());
    let expected = Map::from([("n", Value::from(1)), ("half", Value::from(true))]);
    assert_eq!(*hook.seen.borrow(), [expected.clone(), expected]);
}

#[test]
fn timing_and_lineage_are_off_by_default() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    let out = pipeline.run(&Payload::new()).unwrap();
    assert!(pipeline.state().timings().is_empty());
    assert!(out.lineage().is_empty());
}

#[test]
fn observe_turns_timing_on_and_lineage_when_asked() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_tap(SeeTap {
        seen: Rc::default(),
    });
    pipeline.add_valve(IsOnPredicate, AddOtherFilter);
    pipeline.observe(true, true);
    let out = pipeline.run(&Payload::new()).unwrap();
    let state = pipeline.state();
    let timed: Vec<&str> = state
        .timings()
        .iter()
        .map(|(label, _)| label.as_str())
        .collect();
    assert_eq!(timed, ["AddFilter", "AddOtherFilter"]);
    assert_eq!(out.lineage(), ["AddFilter", "AddOtherFilter"]);
}

#[test]
fn each_run_starts_with_a_new_state() {
    let mut pipeline = Pipeline::new();
    pipeline.add_valve(IsOnPredicate, AddFilter);
    pipeline
        .run(&Payload::from_map(Map::from([("on", false)])))
        .unwrap();
    pipeline
        .run(&Payload::from_map(Map::from([("on", true)])))
        .unwrap();
    assert_eq!(pipeline.state().executed(), ["AddFilter"]);
    assert!(pipeline.state().skipped().is_empty());
}

struct FailIfAskedFilter;
impl Filter for FailIfAskedFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        if payload.get("fail") == Some(&Value::Bool(true)) {
            return Err("asked to fail".into());
        }
        Ok(())
    }
}
struct FailIfAskedTap;
impl Tap for FailIfAskedTap {
    fn observe(&self, payload: &Payload) -> Result<(), StepError> {
        if payload.get("tap_fail") == Some(&Value::Bool(true)) {
            return Err("asked to fail".into());
        }
        Ok(())
    }
}

#[test]
fn a_shorter_run_after_a_longer_one_keeps_nothing_of_it() {
    let mut pipeline = Pipeline::new();
    pipeline.observe(true, false);
    pipeline.add_filter(FailIfAskedFilter);
    pipeline.add_valve(IsOnPredicate, AddFilter);
    pipeline.add_tap(FailIfAskedTap);

    pipeline
        .run(&Payload::from_map(Map::from([
            ("on", true),
            ("tap_fail", true),
        ])))
        .unwrap();
    let state = pipeline.state();
    assert_eq!(
        state.executed(),
        ["FailIfAskedFilter", "AddFilter", "FailIfAskedTap"]
    );
    assert_eq!(state.errors().len(), 1);
    let timed: Vec<&str> = state
        .timings()
        .iter()
        .map(|(label, _)| label.as_str())
        .collect();
    assert_eq!(timed, ["FailIfAskedFilter", "AddFilter"]);

    pipeline
        .run(&Payload::from_map(Map::from([("fail", true)])))
        .unwrap_err();
    let state = pipeline.state();
    assert!(state.executed().is_empty());
    assert!(state.skipped().is_empty());
    assert!(state.errors().is_empty());
    let timed: Vec<&str> = state
        .timings()
        .iter()
        .map(|(label, _)| label.as_str())
        .collect();
    assert_eq!(timed, ["FailIfAskedFilter"]);

    pipeline
        .run(&Payload::from_map(Map::from([("on", false)])))
        .unwrap();
    let state = pipeline.state();
    assert_eq!(state.executed(), ["FailIfAskedFilter", "FailIfAskedTap"]);
    assert_eq!(state.skipped(), ["AddFilter"]);
    assert!(state.errors().is_empty());
}

struct FailingInnerPipeline;
impl NamedPipeline for FailingInnerPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_filter(FailFilter);
    }
}

#[test]
fn a_failure_inside_a_nested_pipeline_is_reported_as_the_nesting_step() {
    let hook = RecordHook::default();
    let mut pipeline = Pipeline::new();
    pipeline.add_pipeline(Pipeline::named(FailingInnerPipeline));
    pipeline.use_hook(hook.clone());
    assert!(pipeline.run(&Payload::new()).is_err());
    assert_eq!(
        hook.events(),
        [
            "before:",
            "before:FailingInnerPipeline",
            "error:FailingInnerPipeline",
            "error:"
        ]
    );
}
