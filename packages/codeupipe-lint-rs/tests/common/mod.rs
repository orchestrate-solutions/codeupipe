// Helpers for the tests: write source text to a new directory and lint it.
#![allow(dead_code)]

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use codeupipe_lint::{lint_paths, Finding, LintOptions};

static MADE: AtomicUsize = AtomicUsize::new(0);

/// A new, empty directory with `files` in it (name, text).
pub fn project(files: &[(&str, &str)]) -> PathBuf {
    let root = std::env::temp_dir().join(format!(
        "cup-lint-rs-{}-{}",
        std::process::id(),
        MADE.fetch_add(1, Ordering::SeqCst)
    ));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(&root).unwrap();
    for (name, text) in files {
        let path = root.join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, text).unwrap();
    }
    root
}

pub struct Linted {
    /// One string for each finding: `file:line rule`.
    pub found: Vec<String>,
    pub findings: Vec<Finding>,
    pub suppressed: usize,
    pub report: String,
    pub exit_code: i32,
}

pub fn lint_in(files: &[(&str, &str)], options: LintOptions) -> Linted {
    let root = project(files);
    let out = lint_paths(&[root.to_string_lossy().into_owned()], &options).unwrap();
    let found = out
        .findings
        .iter()
        .map(|f| format!("{}:{} {}", relative(&root, &f.path), f.line, f.rule))
        .collect();
    let _ = fs::remove_dir_all(&root);
    Linted {
        found,
        findings: out.findings,
        suppressed: out.suppressed.len(),
        report: out.report,
        exit_code: out.exit_code,
    }
}

pub fn disable(rules: &[&str]) -> LintOptions {
    LintOptions {
        disable: rules.iter().map(|rule| rule.to_string()).collect(),
        ..LintOptions::default()
    }
}

fn relative(root: &Path, path: &str) -> String {
    Path::new(path)
        .strip_prefix(root)
        .unwrap()
        .to_string_lossy()
        .into_owned()
}
