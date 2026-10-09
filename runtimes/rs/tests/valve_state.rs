//! A Valve that skips its filter is recorded in `state.skipped`, not
//! `state.executed` (conformance/cases/valve.json). The pipeline stores
//! filters type-erased, so it has to ask the Filter, not downcast it.
mod support;
use codeupipe_core::{Payload, Pipeline, Predicate, Valve, Value};
use support::Set;

struct OpenGate;
impl Predicate for OpenGate {
    fn test(&self, _: &Payload) -> bool {
        true
    }
}

struct ShutGate;
impl Predicate for ShutGate {
    fn test(&self, _: &Payload) -> bool {
        false
    }
}

#[test]
fn a_skipping_valve_is_recorded_as_skipped() {
    let open = Valve::new(Set("x", 1), OpenGate);
    let shut = Valve::new(Set("y", 1), ShutGate);
    let mut p = Pipeline::new().add_filter(open).add_filter(shut);

    let out = p.run(Payload::new()).unwrap();

    assert_eq!(out.get("x").and_then(Value::as_int), Some(1));
    assert!(out.get("y").is_none());
    // a Valve is identified by its inner filter (step identity)
    assert_eq!(p.state().executed, ["valve_state::support::Set"]);
    assert_eq!(p.state().skipped, ["valve_state::support::Set#2"]);
}
