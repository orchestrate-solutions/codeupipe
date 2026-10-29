use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;
use crate::refusal::Refusal;

/// A file that exists is never written over.
///
/// Reads `root`, `component_path` and `test_path`. Both files are checked
/// before one is written, so the command writes both or neither. Each file
/// that is there already is named, with the word `exists`, and the run is
/// refused with exit code 1.
pub struct RefuseExistingFilter;

impl Filter<AddRun> for RefuseExistingFilter {
    fn call(&self, run: &mut AddRun) -> Result<(), StepError> {
        let root = Path::new(&run.root);
        let there: Vec<&String> = [&run.component_path, &run.test_path]
            .into_iter()
            .filter(|path| root.join(path).exists())
            .collect();
        if there.is_empty() {
            return Ok(());
        }
        let names: Vec<&str> = there.iter().map(|name| name.as_str()).collect();
        Err(Refusal::exists(&names.join(", ")).into())
    }
}
