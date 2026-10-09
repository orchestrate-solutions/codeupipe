//! Plane B: a Tap failure never halts the pipeline. Rust Taps fail by
//! panicking; the panic is contained, recorded in `state.errors` under the
//! Tap's identity, and the Tap still counts as executed. Same contract in every
//! runtime: conformance/cases/tap.json.
mod support;
use codeupipe_core::{Payload, Pipeline, Value};
use support::{PanickingTap, Set};

#[test]
fn a_panicking_tap_does_not_halt_run() {
    let mut p = Pipeline::new()
        .add_filter(Set("a", 1))
        .add_tap(PanickingTap)
        .add_filter(Set("b", 2));

    let out = p.run(Payload::new()).expect("a tap failure halted the run");

    assert_eq!(out.get("b").and_then(Value::as_int), Some(2));
    let (set, tap) = ("plane_b::support::Set", "plane_b::support::PanickingTap");
    assert_eq!(p.state().executed, [set, tap, "plane_b::support::Set#2"]);
    assert_eq!(p.state().errors.iter().map(|(n, _)| n.as_str()).collect::<Vec<_>>(), [tap]);
}
