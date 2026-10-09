//! The CUP API contract, Rust side (conformance/API.md). Cross-runtime
//! semantics are in conformance/cases; these pin the Rust spellings.
mod support;
use std::sync::{Arc, Mutex};

use codeupipe_core::{Filter, Hook, Payload, Pipeline, Value};
use support::{BoxError, Set};

#[test]
fn payload_has_remove_to_dict() {
    let p = Payload::new().insert("a", Value::Null).insert("b", Value::Int(2));
    assert!(p.has("a"));
    assert!(!p.has("zz"));
    let without = p.remove("a");
    assert_eq!(without.to_dict().len(), 1);
    assert!(p.has("a"), "remove returns a new payload");
}

#[test]
fn mutable_payload_has_and_removes_in_place() {
    let mut m = Payload::new().insert("a", Value::Int(1)).with_mutation();
    m.set("k", Value::Str("v".into()));
    m.remove("a");
    assert!(m.has("k") && !m.has("a"));
    assert_eq!(m.to_immutable().to_dict().len(), 1);
}

struct Boom;
impl Filter for Boom {
    fn call(&self, _: Payload) -> Result<Payload, BoxError> {
        Err("boom".into())
    }
}

struct Record(Arc<Mutex<Vec<String>>>);
impl Hook for Record {
    fn on_error(&self, step: Option<&str>, error: &(dyn std::error::Error + Send + Sync), _: &Payload) {
        // the error itself, not just its message
        self.0.lock().unwrap().push(format!("{}:{}", step.unwrap_or(""), error));
    }
}

#[test]
fn on_error_receives_the_error_itself() {
    let seen = Arc::new(Mutex::new(Vec::new()));
    let mut p = Pipeline::new().add_filter(Boom).use_hook(Box::new(Record(seen.clone())));
    assert!(p.run(Payload::new()).is_err());
    assert_eq!(*seen.lock().unwrap(), ["api_contract::Boom:boom", ":boom"]);
}

#[test]
fn steps_are_identified_by_type_not_name() {
    // add_filter takes no name: the identity is the filter's type path
    let p = Pipeline::new().add_filter(Set("a", 1));
    assert_eq!(p.identities(), ["api_contract::support::Set"]);
}
