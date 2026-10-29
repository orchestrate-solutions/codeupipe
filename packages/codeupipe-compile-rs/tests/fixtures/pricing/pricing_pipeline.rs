use codeupipe::{NamedPipeline, Pipeline};

use super::at_least_predicate::AtLeastPredicate;
use super::audit_tap::AuditTap;
use super::discount_filter::DiscountFilter;
use super::mark_bulk_filter::MarkBulkFilter;

pub struct PricingPipeline;

impl NamedPipeline for PricingPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_filter(DiscountFilter::new(0.1));
        pipeline.add_valve(AtLeastPredicate::new("qty", 10.0), MarkBulkFilter);
        pipeline.add_tap(AuditTap);
    }
}
