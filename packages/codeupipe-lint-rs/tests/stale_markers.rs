// CUP-I009, a warning: a `cup: allow-...` comment that allowed no finding.
mod common;

use codeupipe_lint::LintOptions;
use common::{disable, lint_in};

#[test]
fn a_comment_that_allows_nothing_is_a_warning() {
    let out = lint_in(
        &[(
            "add.rs",
            "// cup: allow-plain it had a loop before
pub fn add(a: i32, b: i32) -> i32 { a + b }
pub const ONE: i32 = 1; // cup: allow-state-read nothing here reads State
/*
 * cup: allow-plian a kind that does not exist
 */
pub const TWO: i32 = 2;
// cup: allow-outside-write Rust has no such rule
pub const THREE: i32 = 3;
",
        )],
        LintOptions::default(),
    );
    assert_eq!(
        out.found,
        [
            "add.rs:1 CUP-I009",
            "add.rs:3 CUP-I009",
            "add.rs:5 CUP-I009",
            "add.rs:8 CUP-I009"
        ]
    );
    assert!(out.findings[0].warning);
    assert!(out.findings[0]
        .message
        .starts_with("The comment `cup: allow-plain` allows nothing. Remove it"));
    assert_eq!(out.findings[1].col, 28);
    assert_eq!(out.exit_code, 0);
    let strict = lint_in(
        &[(
            "add.rs",
            "// cup: allow-plain no reason\npub const ONE: i32 = 1;\n",
        )],
        LintOptions {
            strict: true,
            ..LintOptions::default()
        },
    );
    assert_eq!(strict.exit_code, 1);
}

#[test]
fn a_comment_that_allows_a_finding_is_not_reported_and_text_that_only_names_a_marker_is_not_a_comment(
) {
    let out = lint_in(
        &[(
            "pick.rs",
            "// cup: allow-plain the entry of the program
pub fn pick(list: &[i32]) -> Option<i32> { for each in list { if *each > 0 { return Some(*each); } } None }
pub fn choose(flag: bool) -> i32 { if flag { 1 } else { 2 } } // cup: allow-plain a small helper
/// cup: allow-plain in a doc comment is text of the documentation
pub const HELP: &str = \"say why: // cup: allow-plain <reason>\";
pub const RAW: &str = r#\"// cup: allow-plain\"#;
pub const SLASH: char = '/'; // a char, then cup: allow-plain is not at the start
",
        )],
        LintOptions::default(),
    );
    assert_eq!(out.found, Vec::<String>::new());
    assert_eq!(out.suppressed, 2);
}

#[test]
fn a_comment_for_a_rule_that_is_switched_off_is_not_reported_and_the_rule_can_be_switched_off() {
    let files = [(
        "pick.rs",
        "// cup: allow-plain the entry\npub fn pick(flag: bool) -> i32 { if flag { 1 } else { 2 } }\n",
    )];
    let off = lint_in(&files, disable(&["CUP-I008"]));
    assert_eq!(off.found, Vec::<String>::new());
    assert_eq!(off.suppressed, 0);
    let quiet = lint_in(
        &[(
            "one.rs",
            "// cup: allow-plain no reason\npub const ONE: i32 = 1;\n",
        )],
        disable(&["CUP-I009"]),
    );
    assert_eq!(quiet.found, Vec::<String>::new());
}
