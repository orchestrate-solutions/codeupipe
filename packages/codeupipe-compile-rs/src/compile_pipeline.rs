use codeupipe::{NamedPipeline, Pipeline};

use crate::borrow_text_filter::BorrowTextFilter;
use crate::compile_run::CompileRun;
use crate::emit_module_filter::EmitModuleFilter;
use crate::lower_steps_filter::LowerStepsFilter;
use crate::read_sources_filter::ReadSourcesFilter;
use crate::resolve_pipeline_filter::ResolvePipelineFilter;
use crate::type_keys_filter::TypeKeysFilter;

/// The compiler, as a codeupipe pipeline: `Pipeline::named(CompilePipeline)`.
pub struct CompilePipeline;

impl NamedPipeline<CompileRun> for CompilePipeline {
    fn add_steps(&self, pipeline: &mut Pipeline<CompileRun>) {
        pipeline.add_filter(ReadSourcesFilter); // the paths to syntax trees
        pipeline.add_filter(ResolvePipelineFilter); // the pipeline to a list of steps, with their settings
        pipeline.add_filter(LowerStepsFilter); // each step to a plain function on the struct
        pipeline.add_filter(TypeKeysFilter); // each key to a field with one type
        pipeline.add_filter(BorrowTextFilter); // with text keys, the steps borrow the caller's text
        pipeline.add_filter(EmitModuleFilter); // the struct and the functions to one module
    }
}
