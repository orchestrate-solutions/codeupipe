//! The crate's public API must be usable from outside the crate.
//!
//! `Payload::insert` takes a `Value`, but `Value` lived in a private module
//! and was never re-exported, so no downstream crate could put anything into
//! a Payload. The in-crate unit tests could not notice; the cross-runtime
//! conformance runner (an external crate) did.
use codeupipe_core::{Payload, Value};

#[test]
fn a_downstream_crate_can_insert_and_read_values() {
    let p = Payload::new().insert("n", Value::Int(1)).insert("s", Value::Str("x".into()));

    assert_eq!(p.get("n").and_then(Value::as_int), Some(1));
    assert_eq!(p.get("s").and_then(Value::as_str), Some("x"));
}
