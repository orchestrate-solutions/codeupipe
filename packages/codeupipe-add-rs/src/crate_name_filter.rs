use std::fs;
use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;

/// The name of the crate that the test file imports: the name in
/// `Cargo.toml`, where `-` becomes `_` (conformance/ADD.md, "Rust and Go: the
/// package").
///
/// Reads `root`. Writes `crate_name`. A project with no `Cargo.toml` gets an
/// empty name, and the test file has no `use` line: the command does not
/// refuse a project because of a file that it does not own.
pub struct CrateNameFilter;

impl Filter<AddRun> for CrateNameFilter {
    fn call(&self, run: &mut AddRun) -> Result<(), StepError> {
        let text = fs::read_to_string(Path::new(&run.root).join("Cargo.toml")).unwrap_or_default();
        run.crate_name = name_of(&text);
        Ok(())
    }
}

/// The value of `name` in the `[package]` part of the manifest, before any
/// other table. An empty name says that the manifest has none.
// cup: allow-plain the reading of the manifest: the text of one key, with no TOML reader to add
fn name_of(manifest: &str) -> String {
    let mut in_package = false;
    for line in manifest.lines() {
        let line = line.split('#').next().unwrap_or_default().trim();
        if line.starts_with('[') {
            in_package = line == "[package]" || line.starts_with("[package.");
            continue;
        }
        if !in_package {
            continue;
        }
        if let Some(value) = line.strip_prefix("name") {
            let Some(value) = value.trim().strip_prefix('=') else {
                continue;
            };
            let value = value.trim().trim_matches(|c| c == '"' || c == '\'');
            return value.replace('-', "_");
        }
    }
    String::new()
}
