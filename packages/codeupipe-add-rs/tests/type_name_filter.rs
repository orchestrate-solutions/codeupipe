// TypeNameFilter: the type name and the file name, from the kind and the
// name, and the refusals of a kind or a name that cannot be used.
use codeupipe_add::{add, AddRun};
use std::fs;
use std::path::PathBuf;

/// A new, empty project for one call, so that no test writes where the tests
/// run. It stays: the machine clears it.
fn project() -> PathBuf {
    let directory = std::env::temp_dir().join(format!(
        "cup-add-names-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |since| since.subsec_nanos())
    ));
    fs::create_dir_all(&directory).expect("the project can be made");
    directory
}
fn type_names(kind: &str, name: &str) -> (String, String) {
    let run = add(AddRun {
        root: project().to_string_lossy().into_owned(),
        kind: kind.to_string(),
        name: name.to_string(),
        ..AddRun::default()
    })
    .expect("the kind and the name can be used");
    (run.type_name, run.snake)
}

fn refused(kind: &str, name: &str) -> (u8, String) {
    let error = add(AddRun {
        root: project().to_string_lossy().into_owned(),
        kind: kind.to_string(),
        name: name.to_string(),
        ..AddRun::default()
    })
    .expect_err("refused");
    (error.exit_code, error.message)
}

#[test]
fn a_name_takes_the_role_of_its_kind() {
    assert_eq!(
        type_names("filter", "Discount"),
        ("DiscountFilter".into(), "discount_filter".into())
    );
    assert_eq!(
        type_names("predicate", "AtLeast"),
        ("AtLeastPredicate".into(), "at_least_predicate".into())
    );
    assert_eq!(
        type_names("tap", "Audit"),
        ("AuditTap".into(), "audit_tap".into())
    );
    assert_eq!(
        type_names("hook", "PrintSteps"),
        ("PrintStepsHook".into(), "print_steps_hook".into())
    );
    assert_eq!(
        type_names("pipeline", "Pricing"),
        ("PricingPipeline".into(), "pricing_pipeline".into())
    );
}

#[test]
fn a_name_with_its_suffix_keeps_it() {
    assert_eq!(
        type_names("filter", "DiscountFilter"),
        ("DiscountFilter".into(), "discount_filter".into())
    );
}

#[test]
fn snake_case_and_kebab_case_become_pascal_case() {
    assert_eq!(type_names("predicate", "at_least").0, "AtLeastPredicate");
    assert_eq!(type_names("tap", "audit-log").0, "AuditLogTap");
    assert_eq!(type_names("tap", "audit-log").1, "audit_log_tap");
}

#[test]
fn capitals_together_are_one_word() {
    assert_eq!(
        type_names("filter", "HTTPGet"),
        ("HTTPGetFilter".into(), "http_get_filter".into())
    );
}

#[test]
fn a_valve_is_not_a_type() {
    let (code, message) = refused("valve", "AtLeast");
    assert_eq!(code, 2);
    assert!(
        message.contains("add_valve(predicate, filter)"),
        "{message}"
    );
}

#[test]
fn the_runtime_makes_a_payload_and_a_state() {
    for kind in ["payload", "state"] {
        let (code, message) = refused(kind, "Order");
        assert_eq!(code, 2, "{kind}");
        assert!(message.contains("runtime"), "{message}");
    }
}

#[test]
fn an_unknown_kind_is_refused() {
    let (code, message) = refused("widget", "Thing");
    assert_eq!(code, 2);
    assert!(
        message.contains("filter, predicate, tap, hook"),
        "{message}"
    );
}

#[test]
fn a_name_that_cannot_be_used_is_refused_with_its_text() {
    for name in ["2Fast", "Take Rate", ""] {
        let (code, message) = refused("filter", name);
        assert_eq!(code, 2, "{name:?}");
        assert!(message.contains(name), "{name:?} in {message}");
    }
}
