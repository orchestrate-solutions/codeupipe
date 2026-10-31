use std::collections::HashMap;

use codeupipe::{Filter, StepError};

use crate::add_run::AddRun;
use crate::crate_name_filter::CrateNameFilter;
use crate::directory_module_filter::DirectoryModuleFilter;
use crate::layout_run::LayoutRun;
use crate::module_line_filter::ModuleLineFilter;
use crate::plan_files_filter::PlanFilesFilter;
use crate::refusal::Refusal;
use crate::render_files_filter::module_of;
use crate::type_name_filter::TypeNameFilter;

/// The type name, the paths and the module of each component, as in phase 1.
///
/// Reads `root`, `directory` and `components`. Writes, for each component,
/// `type_name`, `snake`, `component_path`, `test_path` and `module`, and
/// `module_notes`: the lines that the crate needs, each once, in order. It
/// uses the Filters of phase 1, so the names and the notes are the same. A
/// name that phase 1 refuses, or two components with the same type name, are
/// refused with exit code 2.
pub struct NameComponentsFilter;

impl Filter<LayoutRun> for NameComponentsFilter {
    fn call(&self, run: &mut LayoutRun) -> Result<(), StepError> {
        let mut seen: HashMap<String, String> = HashMap::new();
        let mut notes: Vec<String> = Vec::new();
        for component in &mut run.components {
            let mut one = AddRun {
                root: run.root.clone(),
                kind: component.kind.clone(),
                name: component.name.clone(),
                directory: run.directory.clone(),
                ..AddRun::default()
            };
            TypeNameFilter.call(&mut one)?;
            PlanFilesFilter.call(&mut one)?;
            CrateNameFilter.call(&mut one)?;
            DirectoryModuleFilter.call(&mut one)?;
            ModuleLineFilter.call(&mut one)?;
            if let Some(first) = seen.insert(one.type_name.clone(), component.name.clone()) {
                return Err(Refusal::usage(format!(
                    "Two components are {}: {first} and {}.",
                    one.type_name, component.name
                ))
                .into());
            }
            for note in one.module_notes {
                if !notes.contains(&note) {
                    notes.push(note);
                }
            }
            component.module = module_of(&one.component_path);
            component.type_name = one.type_name;
            component.snake = one.snake;
            component.component_path = one.component_path;
            component.test_path = one.test_path;
        }
        run.module_notes = notes;
        Ok(())
    }
}
