use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;

/// The file of a component directory of its own: `src/pricing.rs` for a
/// component in `src/pricing`.
///
/// A directory under `src` is a module only when the crate says so, and the
/// file of that directory says which components it holds. The command writes
/// neither of them: it is not one of the two files of the contract, and the
/// command does not edit a file that is there already
/// (conformance/ADD.md, "Rust and Go: the package"). It asks for each line on
/// stderr instead, which is what ModuleLineFilter writes.
///
/// Reads `component_path`. Writes `directory_module_path`: the file that
/// holds the line for the component, or empty when the component is in `src`
/// itself, or in the root of the project.
pub struct DirectoryModuleFilter;

impl Filter<AddRun> for DirectoryModuleFilter {
    fn call(&self, run: &mut AddRun) -> Result<(), StepError> {
        let directory = Path::new(&run.component_path)
            .parent()
            .map(|parent| parent.to_string_lossy().into_owned())
            .unwrap_or_default();
        if directory != "src" && directory != "." && !directory.is_empty() {
            run.directory_module_path = format!("{directory}.rs");
        }
        Ok(())
    }
}
