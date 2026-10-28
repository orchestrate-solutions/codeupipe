// CUP-A003 and CUP-A005: a step whose type has no place a test can reach,
// and a plain Pipeline nested as a step. A closure or a function as a step
// (CUP-A001, A002, A008) is a compile error in Rust, so it has no rule here.
mod common;

use common::{disable, lint_in};

const HEAD: &str = "use codeupipe::{Filter, NamedPipeline, Payload, Pipeline, Predicate, StepError, Tap};
struct AddFilter;
impl Filter for AddFilter { fn call(&self, _payload: &mut Payload) -> Result<(), StepError> { Ok(()) } }
struct IsOnPredicate;
impl Predicate for IsOnPredicate { fn test(&self, _payload: &Payload) -> bool { true } }
struct InnerPipeline;
impl NamedPipeline for InnerPipeline { fn add_steps(&self, _pipeline: &mut Pipeline) {} }
";

fn build(body: &str) -> common::Linted {
    let text = format!("{HEAD}{body}");
    lint_in(
        &[("build.rs", &text)],
        disable(&["CUP-I005", "CUP-I006", "CUP-I008"]),
    )
}

#[test]
fn named_types_at_module_level_are_clean() {
    let out = build(
        "fn build() {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(AddFilter);
    pipeline.add_valve(IsOnPredicate, AddFilter);
    let kept = AddFilter;
    pipeline.add_filter(kept.clone());
    pipeline.add_tap(audit::AuditTap::new());
    pipeline.add_pipeline(Pipeline::named(InnerPipeline));
}
",
    );
    assert_eq!(out.found, Vec::<String>::new());
    assert_eq!(out.exit_code, 0);
    assert_eq!(out.report, "No findings.");
}

#[test]
fn a003_a_type_that_is_declared_in_a_function() {
    let out = build(
        "fn build() {
    struct LocalFilter;
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(LocalFilter);
    let kept = LocalFilter;
    pipeline.add_filter(kept);
    pipeline.add_valve(IsOnPredicate, LocalFilter {});
    pipeline.add_tap(LocalTap::new());
    pipeline.add_pipeline(Pipeline::named(LocalPipeline));
    struct LocalTap;
    struct LocalPipeline;
    fn helper(pipeline: &mut Pipeline) {
        pipeline.add_filter(LocalFilter);
    }
}
",
    );
    assert_eq!(
        out.found,
        [
            "build.rs:11 CUP-A003",
            "build.rs:13 CUP-A003",
            "build.rs:14 CUP-A003",
            "build.rs:15 CUP-A003",
            "build.rs:16 CUP-A003",
            "build.rs:20 CUP-A003"
        ]
    );
    assert!(out.findings[0].message.starts_with(
        "Filter is an instance of `LocalFilter`, a type that is declared in a function. Declare it"
    ));
    assert!(out.findings[1]
        .message
        .starts_with("Filter `kept` is an instance of `LocalFilter`,"));
    assert!(out.findings[2].message.starts_with("Valve filter is"));
    assert_eq!(out.exit_code, 1);
}

#[test]
fn a005_a_plain_pipeline_as_a_step() {
    let out = build(
        "fn build() {
    let mut pipeline = Pipeline::new();
    pipeline.add_pipeline(Pipeline::new());
    let mut inner = Pipeline::new();
    inner.add_filter(AddFilter);
    pipeline.add_pipeline(inner);
    pipeline.add_pipeline(Pipeline::named(InnerPipeline));
    pipeline.add_pipeline(Pipeline::<Payload>::default());
}
",
    );
    assert_eq!(
        out.found,
        [
            "build.rs:10 CUP-A005",
            "build.rs:13 CUP-A005",
            "build.rs:15 CUP-A005"
        ]
    );
    assert!(out.findings[0]
        .message
        .starts_with("Pipeline is a plain `Pipeline::new()`. A nested pipeline must be"));
    assert!(out.findings[1]
        .message
        .starts_with("Pipeline `inner` is a plain `Pipeline::new()`."));
    assert!(out.findings[2]
        .message
        .starts_with("Pipeline is a plain `Pipeline::<Payload>::default()`."));
}

#[test]
fn a_name_from_elsewhere_a_parameter_and_a_name_bound_again_are_not_flagged() {
    let out = build(
        "use other::Imported;
fn build(parameter: Pipeline) {
    let mut pipeline = Pipeline::new();
    pipeline.add_filter(Imported);
    pipeline.add_pipeline(parameter);
    let inner = Pipeline::new();
    let inner = Pipeline::named(InnerPipeline);
    pipeline.add_pipeline(inner);
    pipeline.add_filter(other::LocalFilter);
    let make = |inner: Pipeline| pipeline.add_pipeline(inner);
    for inner in list { pipeline.add_pipeline(inner); }
}
",
    );
    assert_eq!(out.found, Vec::<String>::new());
}

#[test]
fn the_add_steps_of_a_named_pipeline_is_checked_too() {
    let out = lint_in(
        &[(
            "pricing_pipeline.rs",
            "use codeupipe::{NamedPipeline, Pipeline};
pub struct PricingPipeline;
impl NamedPipeline for PricingPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_pipeline(Pipeline::new());
    }
}
",
        )],
        Default::default(),
    );
    assert_eq!(out.found, ["pricing_pipeline.rs:5 CUP-A005"]);
}

#[test]
fn allow_anonymous_suppresses_a_finding_on_its_line_the_line_above_or_the_line_of_the_call() {
    let out = build(
        "fn build() {
    struct LocalFilter;
    let mut pipeline = Pipeline::new();
    pipeline.add_pipeline(Pipeline::new()); // cup: allow-anonymous a test of the refusal
    // cup: allow-anonymous
    pipeline.add_pipeline(Pipeline::new());
    pipeline.add_valve( // cup: allow-anonymous
        IsOnPredicate,
        LocalFilter,
    );
    pipeline.add_pipeline(Pipeline::new());
}
",
    );
    assert_eq!(out.found, ["build.rs:18 CUP-A005"]);
    assert_eq!(out.suppressed, 3);
    assert!(out.report.ends_with("1 finding (3 suppressed)."));
}
