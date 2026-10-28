use codeupipe::{NamedPipeline, Pipeline};

/// A named pipeline type, for a pipeline that is a step of another. The
/// runner adds the steps of the case after it is made.
pub struct NestedPipeline;

impl NamedPipeline for NestedPipeline {
    fn add_steps(&self, _pipeline: &mut Pipeline) {}
}
