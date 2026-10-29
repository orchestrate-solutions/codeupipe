use codeupipe::{NamedPipeline, Pipeline};

use super::note_filter::NoteFilter;
use super::trim_name_filter::TrimNameFilter;
use super::vip_predicate::VipPredicate;

/// The caller's note passes through when the guest is not a VIP.
pub struct GreetPipeline;

impl NamedPipeline for GreetPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_filter(TrimNameFilter);
        pipeline.add_valve(VipPredicate, NoteFilter);
    }
}
