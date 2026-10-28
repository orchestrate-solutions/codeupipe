// CUP-I003, I005, I006, I007, and CUP-I000. A write to the Payload outside a
// Filter (CUP-I004) is a compile error in Rust, so it has no rule here.
mod common;

use codeupipe_lint::LintOptions;
use common::lint_in;

#[test]
fn i003_a_filter_or_a_predicate_that_reads_state() {
    let out = lint_in(
        &[
            (
                "count_filter.rs",
                "use std::rc::Rc;
use codeupipe::{Filter, Payload, Pipeline, State, StepError};
pub struct CountFilter {
    pipeline: Rc<Pipeline>,
    seen: Rc<State>,
    states: Vec<State>,
}
impl Filter for CountFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert(\"a\", self.pipeline.state().executed().len());
        payload.insert(\"b\", self.seen.skipped().len());
        payload.insert(\"c\", self.states.len());
        payload.insert(\"d\", payload.get(\"state\").is_some());
        let state = State::new();
        payload.insert(\"e\", state.executed().len() + self.state());
        Ok(())
    }
}
",
            ),
            (
                "ran_predicate.rs",
                "pub struct RanPredicate { holder: Holder }
impl Predicate for RanPredicate {
    fn test(&self, _payload: &Payload) -> bool { !self.holder.state().executed().is_empty() }
}
",
            ),
            (
                "watch_tap.rs",
                "pub struct WatchTap { pipeline: Rc<Pipeline> }
impl Tap for WatchTap {
    fn observe(&self, _payload: &Payload) -> Result<(), StepError> {
        println!(\"{:?}\", self.pipeline.state().executed());
        Ok(())
    }
}
",
            ),
        ],
        LintOptions::default(),
    );
    assert_eq!(
        out.found,
        [
            "count_filter.rs:10 CUP-I003",
            "count_filter.rs:11 CUP-I003",
            "ran_predicate.rs:3 CUP-I003"
        ]
    );
    assert!(out.findings[0]
        .message
        .starts_with("Step reads pipeline State (`self.pipeline.state()`). A Filter's result"));
    assert!(out.findings[1]
        .message
        .starts_with("Step reads pipeline State (`self.seen`)."));
}

const FILTER: &str = "fn call(&self, _payload: &mut Payload) -> Result<(), StepError> { Ok(()) }";
const TAP: &str = "fn observe(&self, _payload: &Payload) -> Result<(), StepError> { Ok(()) }";

#[test]
fn i005_one_primitive_in_each_file() {
    let set_filter = format!(
        "pub struct SetFilter;
impl Filter for SetFilter {{ {FILTER} }}
struct Helper;
pub struct SeeTap;
impl Tap for SeeTap {{ {TAP} }}
fn make() {{ struct LocalFilter; impl Filter for LocalFilter {{ {FILTER} }} }}
"
    );
    let two = format!(
        "struct AFilter;\nimpl Filter for AFilter {{ {FILTER} }}\nstruct BFilter;\nimpl Filter for BFilter {{ {FILTER} }}\n"
    );
    let out = lint_in(
        &[("set_filter.rs", &set_filter), ("tests/steps.rs", &two)],
        LintOptions::default(),
    );
    assert_eq!(
        out.found,
        ["set_filter.rs:4 CUP-I005", "set_filter.rs:4 CUP-I006"]
    );
    assert!(out.findings[0]
        .message
        .starts_with("Tap `SeeTap` shares this file with Filter `SetFilter`."));
}

#[test]
fn i006_the_file_name_is_the_type_name_in_snake_case() {
    let out = lint_in(
        &[
            (
                "discount.rs",
                &format!("pub struct DiscountFilter;\nimpl Filter for DiscountFilter {{ {FILTER} }}\n"),
            ),
            (
                "parse_html_filter.rs",
                &format!("pub struct ParseHTMLFilter;\nimpl Filter for ParseHTMLFilter {{ {FILTER} }}\n"),
            ),
            (
                "pricing_pipeline.rs",
                "pub struct PricingPipeline;\nimpl NamedPipeline for PricingPipeline { fn add_steps(&self, _pipeline: &mut Pipeline) {} }\n",
            ),
            (
                "order_filter.rs",
                &format!("impl<P: PipelineData> codeupipe::Filter<P> for OrderFilter<P> {{ {FILTER} }}\n"),
            ),
        ],
        LintOptions::default(),
    );
    assert_eq!(out.found, ["discount.rs:1 CUP-I006"]);
    assert!(out.findings[0]
        .message
        .starts_with("`DiscountFilter` is in `discount.rs`. Put it in `discount_filter.rs`."));
}

#[test]
fn i007_the_type_name_ends_with_its_role() {
    let out = lint_in(
        &[
            (
                "discount.rs",
                &format!("pub struct Discount;\nimpl Filter for Discount {{ {FILTER} }}\n"),
            ),
            (
                "audit.rs",
                &format!("pub struct Audit;\nimpl codeupipe::Tap for Audit {{ {TAP} }}\n"),
            ),
            (
                "at_least.rs",
                "pub struct AtLeast;\nimpl Predicate for AtLeast { fn test(&self, _p: &Payload) -> bool { true } }\n",
            ),
            (
                "print_steps.rs",
                "pub struct PrintSteps;\nimpl Hook for PrintSteps {}\n",
            ),
            (
                "pricing.rs",
                "pub struct Pricing;\nimpl NamedPipeline for Pricing { fn add_steps(&self, _pipeline: &mut Pipeline) {} }\n",
            ),
            (
                "point.rs",
                "pub struct Point;\nimpl Point { fn call(&self, a: i32, b: i32) {} fn test(&self) {} }\n",
            ),
        ],
        LintOptions::default(),
    );
    assert_eq!(
        out.found,
        [
            "at_least.rs:1 CUP-I006",
            "at_least.rs:1 CUP-I007",
            "audit.rs:1 CUP-I006",
            "audit.rs:1 CUP-I007",
            "discount.rs:1 CUP-I006",
            "discount.rs:1 CUP-I007",
            "pricing.rs:1 CUP-I006",
            "pricing.rs:1 CUP-I007",
            "print_steps.rs:1 CUP-I006",
            "print_steps.rs:1 CUP-I007"
        ]
    );
    assert!(out.findings[1]
        .message
        .starts_with("Predicate `AtLeast` does not say what it is. Name it `AtLeastPredicate`."));
}

#[test]
fn the_comment_markers_suppress_the_invariant_findings() {
    let out = lint_in(
        &[(
            "discount.rs",
            &format!(
                "// cup: allow-name\n#[derive(Clone)]\n// cup: allow-name a name from the paper\npub struct Discount;\nimpl Filter for Discount {{ {FILTER} }}\n"
            ),
        )],
        LintOptions::default(),
    );
    // The first marker is not directly above the struct, so it allows nothing.
    assert_eq!(out.found, ["discount.rs:1 CUP-I009"]);
    assert_eq!(out.suppressed, 2);
}

#[test]
fn a_file_with_a_syntax_error_is_i000() {
    let out = lint_in(&[("broken.rs", "pub struct {{{\n")], LintOptions::default());
    assert_eq!(out.found, ["broken.rs:1 CUP-I000"]);
    assert!(out.findings[0]
        .message
        .ends_with("Fix the syntax error so the file can be checked."));
    assert_eq!(out.exit_code, 1);
}
