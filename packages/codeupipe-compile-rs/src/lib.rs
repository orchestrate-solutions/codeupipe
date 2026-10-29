//! codeupipe-compile: writes a codeupipe pipeline in Rust as plain Rust: a
//! struct with one field for each key, and one function for each step, with
//! no codeupipe. Code that compiles gives the output of the pipeline. A
//! pipeline for which the compiler cannot keep that rule is refused, with
//! the place.
mod compile_pipeline;
mod compile_run;
mod emit_module_filter;
mod key_type;
mod key_use;
mod lower_steps_filter;
mod lowered_step;
mod payload_rewriter;
mod place;
mod read_sources_filter;
mod refusal;
mod resolve_pipeline_filter;
mod source;
mod step;
mod type_keys_filter;

pub use compile_pipeline::CompilePipeline;
pub use compile_run::CompileRun;
pub use place::Place;
pub use refusal::Refusal;

use codeupipe::Pipeline;

/// Compiles the pipeline `pipeline` (the name of its type) from the Rust files under `paths`, to the text of a module.
// cup: allow-plain the entry of the library: it runs the compile pipeline and gives the module or the refusal
pub fn compile(paths: &[String], pipeline: &str) -> Result<String, Refusal> {
    let run = CompileRun {
        paths: paths.to_vec(),
        pipeline: pipeline.to_string(),
        ..CompileRun::default()
    };
    match Pipeline::named(CompilePipeline).run(&run) {
        Ok(done) => Ok(done.module),
        Err(error) => match error.downcast::<Refusal>() {
            Ok(refusal) => Err(*refusal),
            Err(other) => Err(Refusal::new(
                Place {
                    path: paths.first().cloned().unwrap_or_default(),
                    line: 0,
                    col: 0,
                },
                format!("The compiler could not run: {other}"),
                "Check that the files can be read",
            )),
        },
    }
}
