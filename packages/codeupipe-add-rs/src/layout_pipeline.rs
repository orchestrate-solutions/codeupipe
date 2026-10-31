use codeupipe::{NamedPipeline, Pipeline};

use crate::check_layout_filter::CheckLayoutFilter;
use crate::layout_run::LayoutRun;
use crate::name_components_filter::NameComponentsFilter;
use crate::read_layout_filter::ReadLayoutFilter;
use crate::render_layout_filter::RenderLayoutFilter;
use crate::resolve_steps_filter::ResolveStepsFilter;
use crate::stale_pipelines_filter::StalePipelinesFilter;
use crate::write_layout_filter::WriteLayoutFilter;

/// `codeupipe add --layout`, as a codeupipe pipeline:
/// `Pipeline::named(LayoutPipeline)` (conformance/ADD.md, "Phase 2: a layout").
///
/// The seven steps of the Python command. The whole layout is checked before
/// a file is written: a step that cannot go on stops the run with
/// [`Refusal`].
///
/// [`Refusal`]: crate::Refusal
pub struct LayoutPipeline;

impl NamedPipeline<LayoutRun> for LayoutPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline<LayoutRun>) {
        pipeline.add_filter(ReadLayoutFilter); // the file, as data
        pipeline.add_filter(CheckLayoutFilter); // the keys, and the shape of each
        pipeline.add_filter(NameComponentsFilter); // the names, the paths and the module notes of phase 1
        pipeline.add_filter(ResolveStepsFilter); // the calls and the uses of each pipeline
        pipeline.add_filter(RenderLayoutFilter); // the text of the files
        pipeline.add_filter(WriteLayoutFilter); // the files that are not there yet
        pipeline.add_filter(StalePipelinesFilter); // a kept pipeline whose steps changed
    }
}
