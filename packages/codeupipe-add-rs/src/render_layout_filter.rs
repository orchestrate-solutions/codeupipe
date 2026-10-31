use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;
use crate::crate_name_filter::CrateNameFilter;
use crate::layout_run::LayoutRun;
use crate::render_files_filter::RenderFilesFilter;

/// The text of the two files of each component of the layout.
///
/// Reads `root` and `components`. Writes, for each component,
/// `component_text` and `test_text`. It uses the RenderFilesFilter of phase
/// 1, which writes the steps of a pipeline when it has calls.
pub struct RenderLayoutFilter;

impl Filter<LayoutRun> for RenderLayoutFilter {
    fn call(&self, run: &mut LayoutRun) -> Result<(), StepError> {
        for component in &mut run.components {
            let mut one = AddRun {
                root: run.root.clone(),
                kind: component.kind.clone(),
                description: component.description.clone(),
                type_name: component.type_name.clone(),
                snake: component.snake.clone(),
                component_path: component.component_path.clone(),
                calls: component.calls.clone(),
                uses: component.uses.clone(),
                ..AddRun::default()
            };
            CrateNameFilter.call(&mut one)?;
            RenderFilesFilter.call(&mut one)?;
            component.component_text = one.component_text;
            component.test_text = one.test_text;
        }
        Ok(())
    }
}
