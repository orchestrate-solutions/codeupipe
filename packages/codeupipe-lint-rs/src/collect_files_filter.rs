use std::fs;
use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::fnmatch::fnmatch;
use crate::lint_run::LintRun;

/// Directories that hold no source of the project: version control, build
/// output, and dependencies.
const SKIP_DIRS: &[&str] = &[".git", "target", "node_modules"];

/// The Rust files under the given paths.
///
/// Reads `paths` (files or directories) and `exclude` (globs matched against
/// the path of each file). Writes `files`, and `errors` for a path that is
/// not there. Directories are walked in the order of their names.
pub struct CollectFilesFilter;

impl Filter<LintRun> for CollectFilesFilter {
    fn call(&self, run: &mut LintRun) -> Result<(), StepError> {
        let mut found = Vec::new();
        for root in run.paths.clone() {
            let path = Path::new(&root);
            if path.is_dir() {
                Self::walk(path, &mut found);
            } else if path.is_file() {
                found.push(root);
            } else {
                run.errors
                    .push(format!("{root}: no such file or directory"));
            }
        }
        let exclude = &run.exclude;
        run.files = found
            .into_iter()
            .filter(|file| file.ends_with(".rs"))
            .filter(|file| !exclude.iter().any(|pattern| fnmatch(file, pattern)))
            .collect();
        Ok(())
    }
}

impl CollectFilesFilter {
    /// The files under `directory`, in the order of their names.
    fn walk(directory: &Path, found: &mut Vec<String>) {
        let Ok(entries) = fs::read_dir(directory) else {
            return;
        };
        let mut entries: Vec<_> = entries.flatten().map(|entry| entry.path()).collect();
        entries.sort();
        for path in entries {
            let name = path.file_name().unwrap_or_default().to_string_lossy();
            if path.is_dir() && !SKIP_DIRS.contains(&name.as_ref()) {
                Self::walk(&path, found);
            } else if path.is_file() {
                // `./src/x.rs` is `src/x.rs`.
                let path = path.strip_prefix(".").unwrap_or(&path);
                found.push(path.to_string_lossy().into_owned());
            }
        }
    }
}
