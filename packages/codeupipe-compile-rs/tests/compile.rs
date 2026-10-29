// The compiler writes the modules of tests/expected/ from the pipelines of
// tests/fixtures/, and refuses each shape that it cannot keep the same, with
// the place. UPDATE_EXPECTED=1 writes the expected files again; review them.
use std::fs;
use std::path::Path;

use codeupipe_compile::compile;

fn expect_module(fixture: &str, pipeline: &str, expected: &str) {
    let written = compile(&[format!("tests/fixtures/{fixture}")], pipeline)
        .unwrap_or_else(|refusal| panic!("{refusal}"));
    let path = format!("tests/expected/{expected}");
    if std::env::var("UPDATE_EXPECTED").is_ok() {
        fs::write(&path, &written).unwrap();
    }
    // The code is compared, not its layout: cargo fmt can format the expected file in its own way.
    let same_layout = |text: &str| prettyplease::unparse(&syn::parse_file(text).unwrap());
    assert_eq!(
        same_layout(&written),
        same_layout(&fs::read_to_string(&path).unwrap()),
        "{path}"
    );
}

#[test]
fn the_pricing_pipeline_compiles_to_the_expected_module() {
    expect_module("pricing", "PricingPipeline", "pricing.rs");
}

#[test]
fn the_signup_pipeline_compiles_to_the_expected_module() {
    expect_module("signup", "SignupPipeline", "signup.rs");
}

/// A project of one step file and a pipeline file, in a new directory. The step is `step` added with `add`.
fn refused(step: &str, add: &str) -> String {
    let directory =
        std::env::temp_dir().join(format!("cup-compile-{}-{}", std::process::id(), fastrand()));
    fs::create_dir_all(&directory).unwrap();
    fs::write(directory.join("step.rs"), step).unwrap();
    fs::write(
        directory.join("the_pipeline.rs"),
        format!("use codeupipe::{{NamedPipeline, Pipeline}};\npub struct ThePipeline;\nimpl NamedPipeline for ThePipeline {{\n    fn add_steps(&self, pipeline: &mut Pipeline) {{\n        {add}\n    }}\n}}\n"),
    )
    .unwrap();
    let out = compile(&[directory.to_string_lossy().to_string()], "ThePipeline");
    fs::remove_dir_all(&directory).unwrap();
    match out {
        Ok(module) => panic!("compiled, and should be refused:\n{module}"),
        Err(refusal) => refusal.to_string(),
    }
}

/// A number for each project, so that tests that run at the same time have directories of their own.
fn fastrand() -> usize {
    static NEXT: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
}

const HEAD: &str = "use codeupipe::{Filter, Hook, Payload, Predicate, StepError, Value};\npub struct KeyFilter { key: String }\n";

fn assert_refused(message: &str, what: &str, place: &str) {
    assert!(message.contains(what), "{message}");
    assert!(message.contains(place), "{message}");
}

#[test]
fn a_hook_is_refused() {
    let step = "use codeupipe::{Hook, Payload};\npub struct LogHook;\nimpl Hook for LogHook {}\n";
    assert_refused(
        &refused(step, "pipeline.use_hook(LogHook);"),
        "A Hook",
        "the_pipeline.rs:5",
    );
}

#[test]
fn a_key_that_is_not_text_in_the_code_is_refused() {
    let step = format!("{HEAD}pub struct AnyFilter;\nimpl Filter for AnyFilter {{\n    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {{\n        let key = format!(\"k{{}}\", 1);\n        payload.insert(key, 1.0);\n        Ok(())\n    }}\n}}\n");
    assert_refused(
        &refused(&step, "pipeline.add_filter(AnyFilter);"),
        "A key that is not text in the code",
        "step.rs:7",
    );
}

#[test]
fn a_key_with_two_types_is_refused() {
    let step = format!("{HEAD}pub struct AFilter;\nimpl Filter for AFilter {{\n    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {{\n        payload.insert(\"n\", 1.0);\n        Ok(())\n    }}\n}}\npub struct BFilter;\nimpl Filter for BFilter {{\n    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {{\n        payload.insert(\"n\", true);\n        Ok(())\n    }}\n}}\n");
    assert_refused(
        &refused(
            &step,
            "pipeline.add_filter(AFilter);\n        pipeline.add_filter(BFilter);",
        ),
        "The key \"n\" is a number",
        "step.rs:13",
    );
}

#[test]
fn the_payload_given_to_other_code_is_refused() {
    let step = format!("{HEAD}pub struct PrintFilter;\nimpl Filter for PrintFilter {{\n    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {{\n        println!(\"{{:?}}\", payload.to_dict());\n        Ok(())\n    }}\n}}\n");
    assert_refused(
        &refused(&step, "pipeline.add_filter(PrintFilter);"),
        "payload.to_dict()",
        "step.rs:6",
    );
}

#[test]
fn a_read_with_no_type_is_refused() {
    let step = format!("{HEAD}pub struct MatchFilter;\nimpl Filter for MatchFilter {{\n    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {{\n        let n = match payload.get(\"n\") {{ Some(Value::Number(n)) => *n, _ => 0.0 }};\n        payload.insert(\"n\", n + 1.0);\n        Ok(())\n    }}\n}}\n");
    assert_refused(
        &refused(&step, "pipeline.add_filter(MatchFilter);"),
        "and_then(Value::as_f64)",
        "step.rs:6",
    );
}

#[test]
fn a_setting_that_the_constructor_computes_is_refused() {
    let step = format!("{HEAD}pub struct HalfFilter {{ rate: f64 }}\nimpl HalfFilter {{\n    pub fn new(rate: f64) -> Self {{\n        HalfFilter {{ rate: rate / 2.0 }}\n    }}\n}}\nimpl Filter for HalfFilter {{\n    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {{\n        payload.insert(\"rate\", self.rate);\n        Ok(())\n    }}\n}}\n");
    assert_refused(
        &refused(&step, "pipeline.add_filter(HalfFilter::new(1.0));"),
        "computes its setting",
        "step.rs:6",
    );
}

#[test]
fn a_setting_that_is_not_a_literal_is_refused() {
    let step = format!("{HEAD}pub struct RateFilter {{ rate: f64 }}\nimpl RateFilter {{\n    pub fn new(rate: f64) -> Self {{\n        RateFilter {{ rate }}\n    }}\n}}\nimpl Filter for RateFilter {{\n    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {{\n        payload.insert(\"rate\", self.rate);\n        Ok(())\n    }}\n}}\n");
    assert_refused(
        &refused(
            &step,
            "let rate = 0.5;\n        pipeline.add_filter(RateFilter::new(rate));",
        ),
        "not a literal",
        "the_pipeline.rs:6",
    );
}

#[test]
fn a_step_with_no_source_is_refused() {
    let step = HEAD.to_string();
    assert_refused(
        &refused(&step, "pipeline.add_filter(ElsewhereFilter);"),
        "ElsewhereFilter",
        "the_pipeline.rs:5",
    );
}

#[test]
fn a_step_that_calls_a_method_of_its_own_is_refused() {
    let step = format!("{HEAD}pub struct HelpFilter;\nimpl HelpFilter {{\n    fn rate(&self) -> f64 {{ 0.5 }}\n}}\nimpl Filter for HelpFilter {{\n    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {{\n        payload.insert(\"rate\", self.rate());\n        Ok(())\n    }}\n}}\n");
    assert_refused(
        &refused(&step, "pipeline.add_filter(HelpFilter);"),
        "self.rate()",
        "step.rs:9",
    );
}

#[test]
fn the_compiler_refuses_a_pipeline_that_is_not_there() {
    let message = compile(&["tests/fixtures/pricing".to_string()], "NoSuchPipeline")
        .unwrap_err()
        .to_string();
    assert!(message.contains("NoSuchPipeline"), "{message}");
    assert!(Path::new("tests/fixtures/pricing").exists());
}
