use std::fs;
use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;
use crate::refusal::Refusal;

/// The two files, on disk, with the directories that they need.
///
/// Reads `root`, `component_path`, `component_text`, `test_path` and
/// `test_text`. Writes `written`: the two paths of the contract, the
/// component first. These are the only files that the command makes: the
/// module lines that a crate of Rust needs go to stderr instead
/// (ModuleLineFilter), so a project gets no file that the user did not ask
/// for. A directory that cannot be made is refused with exit code 2, before a
/// file is written, so a refusal still leaves the project as it was.
pub struct WriteFilesFilter;

impl Filter<AddRun> for WriteFilesFilter {
    fn call(&self, run: &mut AddRun) -> Result<(), StepError> {
        let root = Path::new(&run.root);
        let files = [
            (run.component_path.as_str(), run.component_text.as_str()),
            (run.test_path.as_str(), run.test_text.as_str()),
        ];
        for (path, _) in &files {
            let parent = root.join(path).parent().map(Path::to_path_buf);
            if let Some(parent) = parent {
                fs::create_dir_all(&parent).map_err(|error| {
                    Refusal::usage(format!("Cannot make the directory of {path}: {error}"))
                })?;
            }
        }
        for (path, text) in &files {
            fs::write(root.join(path), text)
                .map_err(|error| Refusal::usage(format!("Cannot write {path}: {error}")))?;
        }
        run.written = files.iter().map(|(path, _)| (*path).to_string()).collect();
        Ok(())
    }
}
