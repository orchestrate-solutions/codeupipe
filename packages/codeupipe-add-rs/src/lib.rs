//! codeupipe-add: makes the files of a component (conformance/ADD.md).
//!
//! `codeupipe add <kind> <name> [dir] [--description TEXT]` makes the
//! component file and the test file of one component, in the directory where
//! it runs. `codeupipe add --layout cup.layout.yaml` makes those of each
//! component of a layout, and the steps of its pipelines ([`layout`]). The command is a codeupipe pipeline ([`AddPipeline`]) that
//! carries [`AddRun`] in place of a `Payload`: a run holds paths and text,
//! which are the same in each step.
//!
//! ```no_run
//! use codeupipe_add::{add, AddRun};
//!
//! let run = AddRun {
//!     root: ".".to_string(),
//!     kind: "filter".to_string(),
//!     name: "Discount".to_string(),
//!     directory: "src".to_string(),
//!     ..AddRun::default()
//! };
//! for path in add(run)?.written {
//!     println!("{path}");
//! }
//! # Ok::<(), codeupipe_add::Refusal>(())
//! ```

mod add_pipeline;
mod add_run;
mod check_layout_filter;
mod crate_name_filter;
mod directory_module_filter;
mod laid_out;
mod layout_pipeline;
mod layout_run;
mod layout_step;
mod layout_value;
mod module_line_filter;
mod name_components_filter;
mod plan_files_filter;
mod read_layout_filter;
mod refusal;
mod refuse_existing_filter;
mod render_files_filter;
mod render_layout_filter;
mod resolve_steps_filter;
mod stale_pipelines_filter;
mod templates;
mod type_name_filter;
mod write_files_filter;
mod write_layout_filter;

pub use add_pipeline::AddPipeline;
pub use add_run::AddRun;
pub use laid_out::LaidOut;
pub use layout_pipeline::LayoutPipeline;
pub use layout_run::LayoutRun;
pub use layout_step::LayoutStep;
pub use layout_value::LayoutValue;
pub use refusal::Refusal;

use codeupipe::Pipeline;

/// Runs one `add`: the two files, or the refusal and nothing else.
///
/// The paths of `written` are relative to the root of the run, component
/// first, as the contract prints them.
pub fn add(run: AddRun) -> Result<AddRun, Refusal> {
    Pipeline::named(AddPipeline).run(&run).map_err(refusal_of)
}

/// Runs one `add --layout`: the files that it wrote and kept, or the
/// refusal and nothing written.
///
/// `run` has `root` and `layout_path`. The paths of `written`, `kept` and
/// `stale` are relative to the root, component first.
pub fn layout(run: LayoutRun) -> Result<LayoutRun, Refusal> {
    Pipeline::named(LayoutPipeline)
        .run(&run)
        .map_err(refusal_of)
}

/// The Refusal that stopped a run, or one that says what went wrong.
// cup: allow-plain the edge of the library: it turns the error of a run into the Refusal of the contract
fn refusal_of(error: codeupipe::StepError) -> Refusal {
    match error.downcast::<Refusal>() {
        Ok(refusal) => *refusal,
        Err(other) => Refusal::usage(format!(
            "The command could not run: {}. Give a kind, a name, and a directory that can be made.",
            other
        )),
    }
}
