use std::fs;
use std::path::Path;

use codeupipe::{Filter, StepError};

use crate::layout_run::LayoutRun;
use crate::refusal::Refusal;

/// Write each file of the layout that is not there yet (conformance/ADD.md,
/// "Files that exist").
///
/// Reads `root` and `components`. Writes `written` and `kept`: the paths, in
/// order, component first. A file that exists is kept, by itself. The
/// directories are made before a file is written; one that cannot be made is
/// refused with exit code 2.
pub struct WriteLayoutFilter;

impl Filter<LayoutRun> for WriteLayoutFilter {
    fn call(&self, run: &mut LayoutRun) -> Result<(), StepError> {
        let root = Path::new(&run.root);
        let files: Vec<(&String, &String)> = run
            .components
            .iter()
            .flat_map(|component| {
                [
                    (&component.component_path, &component.component_text),
                    (&component.test_path, &component.test_text),
                ]
            })
            .collect();
        let (kept, fresh): (Vec<_>, Vec<_>) = files
            .into_iter()
            .partition(|(path, _)| root.join(path).exists());
        for (path, _) in &fresh {
            if let Some(parent) = root.join(path).parent() {
                fs::create_dir_all(parent).map_err(|error| {
                    Refusal::usage(format!("Cannot make the directory of {path}: {error}"))
                })?;
            }
        }
        for (path, text) in &fresh {
            fs::write(root.join(path), text)?;
        }
        let written = fresh.iter().map(|(path, _)| (*path).clone()).collect();
        let kept = kept.iter().map(|(path, _)| (*path).clone()).collect();
        run.written = written;
        run.kept = kept;
        Ok(())
    }
}
