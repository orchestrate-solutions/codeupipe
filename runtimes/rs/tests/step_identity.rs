//! Step identity (conformance/API.md): a step is identified by its filter's
//! type path (`std::any::type_name`), #n from its second use; no names.
//! Closures and type-erased boxes are refused; a plain Pipeline cannot even
//! be nested (it does not implement `Nestable`: a compile error).

use codeupipe_core::{Filter, Hook, Nestable, Parallel, Payload, Pipeline, Predicate, Tap, Valve, Value};

type BoxError = Box<dyn std::error::Error + Send + Sync>;

struct Inc;
impl Filter for Inc {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        let n = p.get("n").and_then(Value::as_int).unwrap_or(0);
        Ok(p.insert("n", Value::Int(n + 1)))
    }
}

struct Boom;
impl Filter for Boom {
    fn call(&self, _: Payload) -> Result<Payload, BoxError> {
        Err("boom".into())
    }
}

struct Audit;
impl Tap for Audit {
    fn observe(&self, _: &Payload) {}
}

/// A predicate object: a named type, identified by its type path.
struct IsOn;
impl Predicate for IsOn {
    fn test(&self, p: &Payload) -> bool {
        matches!(p.get("on"), Some(Value::Bool(true)))
    }
}

/// A configurable predicate: a named struct, its settings in its fields.
struct AtLeast(i64);
impl Predicate for AtLeast {
    fn test(&self, p: &Payload) -> bool {
        p.get("n").and_then(Value::as_int).unwrap_or(0) >= self.0
    }
}

/// A named pipeline type: the Rust equivalent of a Pipeline subclass.
struct Onboarding(Pipeline);
impl Nestable for Onboarding {
    fn into_pipeline(self) -> Pipeline {
        self.0
    }
}
fn onboarding() -> Onboarding {
    Onboarding(Pipeline::new().add_filter(Inc))
}

#[derive(Default)]
struct Record(std::sync::Mutex<Vec<String>>);
impl Hook for Record {
    fn before(&self, step: Option<&str>, _: &Payload) {
        self.0.lock().unwrap().push(format!("before:{}", step.unwrap_or("")));
    }
    fn after(&self, step: Option<&str>, _: &Payload) {
        self.0.lock().unwrap().push(format!("after:{}", step.unwrap_or("")));
    }
    fn on_error(&self, step: Option<&str>, _: &(dyn std::error::Error + Send + Sync), _: &Payload) {
        self.0.lock().unwrap().push(format!("error:{}", step.unwrap_or("")));
    }
}

#[test]
fn state_reports_the_type_path() {
    let mut p = Pipeline::new().add_filter(Inc);
    p.run(Payload::new()).unwrap();
    assert_eq!(p.state().executed, vec!["step_identity::Inc"]);
}

#[test]
fn reuse_is_numbered_from_the_second_occurrence() {
    let p = Pipeline::new().add_filter(Inc).add_filter(Inc).add_filter(Inc);
    assert_eq!(p.identities(), vec!["step_identity::Inc", "step_identity::Inc#2", "step_identity::Inc#3"]);
}

#[test]
fn taps_and_a_valve_by_its_inner_filter() {
    let mut p = Pipeline::new().add_tap(Audit).add_filter(Valve::new(Inc, IsOn));
    p.run(Payload::new()).unwrap();
    assert_eq!(p.state().executed, vec!["step_identity::Audit"]);
    assert_eq!(p.state().skipped, vec!["step_identity::Inc"]);
}

#[test]
fn a_configurable_predicate_is_a_named_struct() {
    let valve = Valve::new(Inc, AtLeast(5));
    assert_eq!(valve.predicate_symbol(), "step_identity::AtLeast");
    let mut p = Pipeline::new().add_filter(valve);
    let out = p.run(Payload::new().insert("n", Value::Int(5))).unwrap();
    assert_eq!(out.get("n").and_then(Value::as_int), Some(6));
}

#[test]
fn a_named_pipeline_type_nests_as_one_step() {
    let mut outer = Pipeline::new().add_filter(Inc).add_pipeline(onboarding());
    let out = outer.run(Payload::new()).unwrap();
    assert_eq!(out.get("n").and_then(Value::as_int), Some(2));
    assert_eq!(outer.state().executed, vec!["step_identity::Inc", "step_identity::Onboarding"]);
}

#[test]
fn hooks_receive_identities() {
    let hook = std::sync::Arc::new(Record::default());
    struct Shared(std::sync::Arc<Record>);
    impl Hook for Shared {
        fn before(&self, s: Option<&str>, p: &Payload) { self.0.before(s, p) }
        fn after(&self, s: Option<&str>, p: &Payload) { self.0.after(s, p) }
        fn on_error(&self, s: Option<&str>, e: &(dyn std::error::Error + Send + Sync), p: &Payload) {
            self.0.on_error(s, e, p)
        }
    }
    let mut p = Pipeline::new().add_filter(Inc).add_filter(Boom).use_hook(Box::new(Shared(hook.clone())));
    assert!(p.run(Payload::new()).is_err());
    let events = hook.0.lock().unwrap().clone();
    assert_eq!(events, vec!["before:", "before:step_identity::Inc", "after:step_identity::Inc",
        "before:step_identity::Boom", "error:step_identity::Boom", "error:"]);
}

#[test]
fn parallel_members_are_identified() {
    let p = Pipeline::new().add_parallel(Parallel::new().with(Inc).with(Audit2));
    assert_eq!(p.identities(), vec!["parallel[step_identity::Inc,step_identity::Audit2]"]);
}

struct Audit2;
impl Filter for Audit2 {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        Ok(p)
    }
}

#[test]
fn the_add_site_is_recorded() {
    let p = Pipeline::new().add_filter(Inc);
    let site = p.step_sites()["step_identity::Inc"].clone();
    assert!(site.starts_with("tests/step_identity.rs:"), "{site}");
}

// A closure or fn is not a Predicate (there is no impl for them), so passing
// one to Valve::new is a compile error: no runtime refusal to test.

// `Box<dyn Filter>` does not implement Filter, so passing one is a compile
// error. A wrapper around a trait object still type-checks; it is refused
// because its type path names no concrete filter.
struct Erased(Box<dyn Filter>);
impl Filter for Erased {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        self.0.call(p)
    }
}
struct Wrap<T: ?Sized>(Box<T>);
impl Filter for Wrap<dyn Filter> {
    fn call(&self, p: Payload) -> Result<Payload, BoxError> {
        self.0.call(p)
    }
}

#[test]
#[should_panic(expected = "type-erased")]
fn a_wrapper_around_a_trait_object_is_refused() {
    let boxed: Box<dyn Filter> = Box::new(Inc);
    let _ = Pipeline::new().add_filter(Wrap(boxed));
}

#[test]
fn a_named_wrapper_is_its_own_identity() {
    // A named wrapper type is a named declaration: it is the code that runs.
    let p = Pipeline::new().add_filter(Erased(Box::new(Inc)));
    assert_eq!(p.identities(), vec!["step_identity::Erased"]);
}
