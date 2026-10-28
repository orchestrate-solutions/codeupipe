// CUP-I008, a warning: logic that is not in a primitive.
mod common;

use codeupipe_lint::LintOptions;
use common::{disable, lint_in, Linted};

fn warnings(out: &Linted) -> Vec<String> {
    out.findings
        .iter()
        .filter(|f| f.warning)
        .map(|f| f.message.split(" has logic").next().unwrap().to_string())
        .collect()
}

#[test]
fn a_function_with_a_decision_that_is_not_in_a_primitive_is_a_warning() {
    let out = lint_in(
        &[(
            "who_is_due.rs",
            "pub fn who_is_due(entries: &[String]) -> &'static str { if entries.is_empty() { return \"say\"; } \"model\" }
pub fn pick(list: &[i32]) -> Option<i32> { for each in list { if *each > 0 { return Some(*each); } } None }
pub fn choose(flag: bool) -> &'static str { match flag { true => \"a\", false => \"b\" } }
pub fn wait() { loop { break; } }
pub fn plain(a: i32, b: i32) -> i32 { a + b }
pub fn double(list: &[i32]) -> Vec<i32> { list.iter().map(|n| n * 2).collect() }
pub fn first(list: &[i32]) -> i32 { let Some(x) = list.first() else { return 0 }; *x }
",
        )],
        LintOptions::default(),
    );
    assert_eq!(
        out.found,
        [
            "who_is_due.rs:1 CUP-I008",
            "who_is_due.rs:2 CUP-I008",
            "who_is_due.rs:3 CUP-I008",
            "who_is_due.rs:4 CUP-I008",
            "who_is_due.rs:7 CUP-I008"
        ]
    );
    assert_eq!(
        warnings(&out),
        [
            "Function `who_is_due`",
            "Function `pick`",
            "Function `choose`",
            "Function `wait`",
            "Function `first`"
        ]
    );
    assert!(out.findings[0].message.contains(
        "is not a Filter, a Predicate, a Tap, a Hook or a Pipeline. Write it as a primitive"
    ));
}

#[test]
fn a_type_or_a_trait_that_is_not_a_primitive_and_code_at_the_top_of_a_file() {
    let out = lint_in(
        &[
            (
                "record_store.rs",
                "pub struct RecordStore { files: Vec<String> }
impl RecordStore {
    pub fn read(&self, id: &str) -> Vec<String> { if id.is_empty() { return vec![]; } self.files.clone() }
}
pub struct Point { x: f64 }
impl Point { pub fn double(&self) -> f64 { self.x * 2.0 } }
impl std::fmt::Display for Point { fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result { write!(f, \"{}\", self.x) } }
pub trait Choose { fn choose(&self, a: bool) -> i32 { if a { 1 } else { 2 } } }
impl Default for Elsewhere { fn default() -> Self { match 1 { _ => Elsewhere } } }
",
            ),
            (
                "main.rs",
                "const LIMIT: usize = if cfg!(debug_assertions) { 1 } else { 2 };
fn main() { let args: Vec<String> = std::env::args().collect(); if args.is_empty() { std::process::exit(2); } }
",
            ),
            (
                "helpers.rs",
                "pub mod inner {
    pub fn pick(a: bool) -> i32 { if a { 1 } else { 2 } }
}
",
            ),
        ],
        LintOptions::default(),
    );
    assert_eq!(
        out.found,
        [
            "helpers.rs:2 CUP-I008",
            "main.rs:1 CUP-I008",
            "main.rs:2 CUP-I008",
            "record_store.rs:2 CUP-I008",
            "record_store.rs:8 CUP-I008",
            "record_store.rs:9 CUP-I008"
        ]
    );
    assert_eq!(
        warnings(&out),
        [
            "Function `pick`",
            "The code at the top of this file",
            "Function `main`",
            "Type `RecordStore`",
            "Trait `Choose`",
            "Type `Elsewhere`"
        ]
    );
}

#[test]
fn logic_in_a_primitive_is_where_it_must_be_and_types_and_tests_have_no_finding() {
    let out = lint_in(
        &[
            (
                "pick_filter.rs",
                "pub struct PickFilter { on: bool }
impl PickFilter { pub fn new(on: bool) -> Self { if on { PickFilter { on } } else { PickFilter { on: false } } } }
impl Filter for PickFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        if payload.has(\"a\") { payload.insert(\"b\", 1); }
        for _ in 0..2 {}
        Ok(())
    }
}
",
            ),
            (
                "is_on_predicate.rs",
                "pub struct IsOnPredicate;\nimpl Predicate for IsOnPredicate { fn test(&self, p: &Payload) -> bool { match p.get(\"on\") { Some(_) => true, None => false } } }\n",
            ),
            (
                "see_tap.rs",
                "pub struct SeeTap;\nimpl Tap for SeeTap { fn observe(&self, p: &Payload) -> Result<(), StepError> { if p.has(\"x\") { println!(\"x\"); } Ok(()) } }\n",
            ),
            (
                "log_hook.rs",
                "pub struct LogHook;\nimpl Hook for LogHook { fn before(&self, step: Option<&str>, _p: &Payload) { if let Some(step) = step { println!(\"{step}\"); } } }\n",
            ),
            (
                "main_pipeline.rs",
                "pub struct MainPipeline;\nimpl NamedPipeline for MainPipeline { fn add_steps(&self, pipeline: &mut Pipeline) { if std::env::var(\"X\").is_ok() { pipeline.observe(true, false); } } }\n",
            ),
            (
                "types.rs",
                "pub enum Due { Say, Model }
pub trait Model { fn reply(&self, text: &str) -> String; }
pub const LIMIT: usize = 20000;
pub type Names = Vec<String>;
#[test]
fn checks() { if LIMIT > 1 { return; } }
#[cfg(test)]
mod tests {
    fn helper(a: bool) -> i32 { if a { 1 } else { 2 } }
}
",
            ),
        ],
        LintOptions::default(),
    );
    assert_eq!(out.found, Vec::<String>::new());
}

#[test]
fn a_warning_does_not_fail_the_run_unless_the_run_is_strict() {
    let files = [(
        "helper.rs",
        "pub fn pick(a: bool) -> i32 { if a { 1 } else { 2 } }\n",
    )];
    let soft = lint_in(&files, LintOptions::default());
    assert_eq!(soft.exit_code, 0);
    assert!(soft.report.contains(
        "helper.rs:1:8  CUP-I008 logic-outside-primitive  warning: Function `pick` has logic"
    ));
    assert!(soft.report.ends_with("\nNo findings. 1 warning."));
    let strict = lint_in(
        &files,
        LintOptions {
            strict: true,
            ..LintOptions::default()
        },
    );
    assert_eq!(strict.exit_code, 1);
}

#[test]
fn a_warning_and_a_finding_are_counted_apart() {
    let out = lint_in(
        &[(
            "discount.rs",
            "pub struct Discount;
impl Filter for Discount { fn call(&self, _p: &mut Payload) -> Result<(), StepError> { Ok(()) } }
pub fn pick(a: bool) -> i32 { if a { 1 } else { 2 } }
",
        )],
        LintOptions::default(),
    );
    assert_eq!(out.exit_code, 1);
    assert!(out.report.ends_with("\n2 findings. 1 warning."));
}

#[test]
fn allow_plain_with_a_reason_suppresses_the_warning_and_test_files_are_not_checked() {
    let out = lint_in(
        &[
            (
                "helper.rs",
                "/// Picks one.
#[inline]
// cup: allow-plain a pure helper of two Predicates
pub fn pick(a: bool) -> i32 { if a { 1 } else { 2 } }
",
            ),
            (
                "tests/support.rs",
                "pub fn pick(a: bool) -> i32 { if a { 1 } else { 2 } }\n",
            ),
        ],
        LintOptions::default(),
    );
    assert_eq!(out.found, Vec::<String>::new());
    assert_eq!(out.suppressed, 1);
    assert_eq!(out.report, "No findings (1 suppressed).");
}

#[test]
fn the_rule_can_be_switched_off() {
    let out = lint_in(
        &[(
            "helper.rs",
            "pub fn pick(a: bool) -> i32 { if a { 1 } else { 2 } }\n",
        )],
        disable(&["CUP-I008"]),
    );
    assert_eq!(out.found, Vec::<String>::new());
    assert_eq!(out.report, "No findings.");
}
