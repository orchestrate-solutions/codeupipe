use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;
use crate::refusal::Refusal;

/// Where the component file and the test file go.
///
/// Reads `directory` (relative to the root) and `snake`. Writes
/// `component_path` (`src/pricing/discount_filter.rs`) and `test_path`
/// (`tests/discount_filter.rs`), with `/` between the parts, as the contract
/// prints them. A directory that goes out of the root is refused with exit
/// code 2.
pub struct PlanFilesFilter;

impl Filter<AddRun> for PlanFilesFilter {
    fn call(&self, run: &mut AddRun) -> Result<(), StepError> {
        let directory = if run.directory.is_empty() {
            "."
        } else {
            run.directory.as_str()
        };
        if Path::new(directory)
            .components()
            .any(|part| matches!(part, std::path::Component::ParentDir))
        {
            return Err(Refusal::usage(format!(
                "The directory `{directory}` cannot be used. It is relative to the root of the project, and does not go out of it."
            ))
            .into());
        }
        run.component_path = join(directory, &format!("{}.rs", run.snake));
        run.test_path = format!("tests/{}.rs", run.snake);
        Ok(())
    }
}

/// `src/pricing` and `discount_filter.rs` give `src/pricing/discount_filter.rs`.
/// `.` adds nothing.
// cup: allow-plain a path rule of the contract: it joins text, and is not a step
fn join(directory: &str, file: &str) -> String {
    let directory = directory.trim_matches('/');
    if directory.is_empty() || directory == "." {
        return file.to_string();
    }
    let directory = directory.strip_prefix("./").unwrap_or(directory);
    format!("{directory}/{file}")
}
