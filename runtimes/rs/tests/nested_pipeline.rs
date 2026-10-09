//! A nested Pipeline is a step (conformance/cases/pipeline.json). It used to
//! be accepted by add_pipeline and then always fail at run time.
mod support;
use codeupipe_core::{Nestable, Payload, Pipeline, Value};
use support::{Add, Set};

/// A named pipeline type: only these can be nested (step identity).
struct Inner(Pipeline);
impl Nestable for Inner {
    fn into_pipeline(self) -> Pipeline {
        self.0
    }
}

#[test]
fn a_nested_pipeline_runs_as_one_step() {
    let inner = Inner(Pipeline::new().add_filter(Add("a", 1)));
    let mut p = Pipeline::new()
        .add_filter(Set("a", 1))
        .add_pipeline(inner)
        .add_filter(Add("a", 10));

    let out = p.run(Payload::new()).expect("nested pipeline failed");

    assert_eq!(out.get("a").and_then(Value::as_int), Some(12));
    assert_eq!(
        p.state().executed,
        ["nested_pipeline::support::Set", "nested_pipeline::Inner", "nested_pipeline::support::Add"]
    );
}
