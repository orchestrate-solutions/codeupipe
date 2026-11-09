use codeupipe::{NamedPipeline, Pipeline};

use crate::add_run::AddRun;
use crate::crate_name_filter::CrateNameFilter;
use crate::directory_module_filter::DirectoryModuleFilter;
use crate::module_line_filter::ModuleLineFilter;
use crate::plan_files_filter::PlanFilesFilter;
use crate::refuse_existing_filter::RefuseExistingFilter;
use crate::render_files_filter::RenderFilesFilter;
use crate::type_name_filter::TypeNameFilter;
use crate::write_files_filter::WriteFilesFilter;

/// `codeupipe add`, as a codeupipe pipeline: `Pipeline::named(AddPipeline)`.
///
/// The steps are the five of the Python command, with three steps of Rust
/// beside them: the crate name that the test file imports, the `mod.rs` of a
/// component directory of its own, and the module line that `src/lib.rs` must
/// declare. A step that cannot go on stops the run with [`Refusal`], and
/// nothing is written.
///
/// [`Refusal`]: crate::Refusal
pub struct AddPipeline;

impl NamedPipeline<AddRun> for AddPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline<AddRun>) {
        pipeline.add_filter(TypeNameFilter); // kind and name to type name and file name
        pipeline.add_filter(PlanFilesFilter); // the two paths, relative to the root
        pipeline.add_filter(CrateNameFilter); // the name that the test imports
        pipeline.add_filter(RefuseExistingFilter); // a file that exists stops the run
        pipeline.add_filter(RenderFilesFilter); // the text of the two files
        pipeline.add_filter(DirectoryModuleFilter); // the mod.rs of a component directory
        pipeline.add_filter(ModuleLineFilter); // the line for src/lib.rs, on stderr
        pipeline.add_filter(WriteFilesFilter); // the files, on disk
    }
}
