// The command: its exit codes, arguments, config file, and the linter on
// the Rust code of this repository.
mod common;

use std::path::Path;
use std::process::Command;

use codeupipe_lint::LintOptions;
use common::{lint_in, project};

const BAD: &str = "pub struct Discount;
impl Filter for Discount { fn call(&self, _p: &mut Payload) -> Result<(), StepError> { Ok(()) } }
";
const GOOD: &str = "pub struct SetFilter;
impl Filter for SetFilter { fn call(&self, _p: &mut Payload) -> Result<(), StepError> { Ok(()) } }
";

struct Ran {
    code: i32,
    out: String,
    err: String,
}

fn run(cwd: &Path, args: &[&str]) -> Ran {
    let done = Command::new(env!("CARGO_BIN_EXE_codeupipe-lint"))
        .args(args)
        .current_dir(cwd)
        .output()
        .unwrap();
    Ran {
        code: done.status.code().unwrap(),
        out: String::from_utf8(done.stdout).unwrap(),
        err: String::from_utf8(done.stderr).unwrap(),
    }
}

#[test]
fn exit_0_with_no_findings_exit_1_with_findings_one_line_for_each() {
    let root = project(&[("discount.rs", BAD), ("set_filter.rs", GOOD)]);
    let clean = run(&root, &["set_filter.rs"]);
    assert_eq!(clean.code, 0);
    assert_eq!(clean.out.trim(), "No findings.");
    let bad = run(&root, &["."]);
    assert_eq!(bad.code, 1);
    assert!(
        bad.out
            .starts_with("discount.rs:1:12  CUP-I006 primitive-file-name  "),
        "{}",
        bad.out
    );
    assert!(bad.out.ends_with("\n2 findings.\n"));
}

#[test]
fn exit_2_for_a_path_that_is_not_there_a_rule_that_is_not_known_and_no_paths() {
    let root = project(&[]);
    let missing = run(&root, &["nothing-here"]);
    assert_eq!(missing.code, 2);
    assert!(missing
        .err
        .contains("error: nothing-here: no such file or directory"));
    let unknown = run(&root, &["--disable", "CUP-X999", "."]);
    assert_eq!(unknown.code, 2);
    assert!(unknown.err.contains("no such rule: CUP-X999"));
    // A rule that the compiler checks in Rust is not a rule of this linter.
    assert_eq!(run(&root, &["--disable", "CUP-A001", "."]).code, 2);
    assert_eq!(run(&root, &[]).code, 2);
    assert_eq!(run(&root, &["--nope", "."]).code, 2);
}

#[test]
fn rules_lists_the_rule_ids() {
    let listed = run(&project(&[]), &["--rules"]);
    assert_eq!(listed.code, 0);
    assert_eq!(
        listed.out,
        "CUP-A003  local-type-step
CUP-A005  unnamed-pipeline-step
CUP-I000  parse-error
CUP-I003  state-read-in-step
CUP-I005  one-primitive-per-file
CUP-I006  primitive-file-name
CUP-I007  primitive-role-suffix
CUP-I008  logic-outside-primitive
CUP-I009  marker-allows-nothing
"
    );
}

#[test]
fn exclude_and_disable() {
    let root = project(&[("discount.rs", BAD)]);
    assert_eq!(
        run(
            &root,
            &[
                "--exclude",
                "*/discount.rs",
                "--exclude",
                "discount.rs",
                "."
            ]
        )
        .code,
        0
    );
    assert_eq!(
        run(&root, &["--disable", "CUP-I006", "--disable=CUP-I007", "."]).code,
        0
    );
    assert_eq!(run(&root, &["--disable", "CUP-I006", "."]).code, 1);
}

#[test]
fn with_no_paths_they_come_from_cup_config_json() {
    let root = project(&[
        ("discount.rs", BAD),
        (
            "cup.config.json",
            r#"{"lint": {"paths": ["."], "disable": ["CUP-I006", "CUP-I007"]}, "deploy": {}}"#,
        ),
    ]);
    assert_eq!(run(&root, &[]).code, 0);
    assert_eq!(run(&root, &["discount.rs"]).code, 1);
    std::fs::write(root.join("cup.config.json"), r#"{"lint": {"path": ["."]}}"#).unwrap();
    let wrong = run(&root, &[]);
    assert_eq!(wrong.code, 2);
    assert!(wrong.err.contains("unknown key 'path'"), "{}", wrong.err);
    std::fs::write(root.join("cup.config.json"), r#"{"lint": {"paths": "."}}"#).unwrap();
    assert!(run(&root, &[])
        .err
        .contains("lint.paths must be a list of strings"));
    assert!(run(&root, &["--config", "other.json"])
        .err
        .contains("other.json: no such file"));
}

#[test]
fn target_and_git_are_not_read() {
    let out = lint_in(
        &[("target/debug/discount.rs", BAD), (".git/discount.rs", BAD)],
        LintOptions::default(),
    );
    assert_eq!(out.found, Vec::<String>::new());
}

#[test]
fn the_linter_is_clean_on_the_rust_code_of_this_repository() {
    let here = Path::new(env!("CARGO_MANIFEST_DIR"));
    let done = run(
        here,
        &[
            "--strict",
            "src",
            "tests",
            "../codeupipe-rs/src",
            "../codeupipe-rs/examples",
            "../codeupipe-rs/tests",
            "../../conformance/runners/rust/src",
        ],
    );
    // Each plain logic of this repository says why, with `cup: allow-plain`.
    assert!(
        done.out.starts_with("No findings (") && !done.out.contains("warning"),
        "{}",
        done.out
    );
    assert_eq!(done.code, 0);
}
