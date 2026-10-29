//! codeupipe-add: makes the files of a component (conformance/ADD.md).
//!
//! `codeupipe add <kind> <name> [dir] [--description TEXT]` makes the
//! component file and the test file of one component, in the directory where
//! it runs. The command is a codeupipe pipeline ([`AddPipeline`]) that
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
mod crate_name_filter;
mod directory_module_filter;
mod module_line_filter;
mod plan_files_filter;
mod refusal;
mod refuse_existing_filter;
mod render_files_filter;
mod templates;
mod type_name_filter;
mod write_files_filter;

pub use add_pipeline::AddPipeline;
pub use add_run::AddRun;
pub use refusal::Refusal;

use codeupipe::Pipeline;

/// Runs one `add`: the two files, or the refusal and nothing else.
///
/// The paths of `written` are relative to the root of the run, component
/// first, as the contract prints them.
// cup: allow-plain the entry of the library: it runs the add pipeline and gives the run or the refusal
pub fn add(run: AddRun) -> Result<AddRun, Refusal> {
    match Pipeline::named(AddPipeline).run(&run) {
        Ok(done) => Ok(done),
        Err(error) => match error.downcast::<Refusal>() {
            Ok(refusal) => Err(*refusal),
            Err(other) => Err(Refusal::usage(format!(
                "The command could not run: {}. Give a kind, a name, and a directory that can be made.",
                other
            ))),
        },
    }
}
