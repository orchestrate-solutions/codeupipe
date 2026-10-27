use codeupipe::{NamedPipeline, Pipeline};

use crate::at_least_predicate::AtLeastPredicate;
use crate::audit_tap::AuditTap;
use crate::discount_filter::DiscountFilter;
use crate::mark_bulk_filter::MarkBulkFilter;

/// A named pipeline: `Pipeline::named(PricingPipeline)`.
pub struct PricingPipeline;

impl NamedPipeline for PricingPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline) {
        pipeline.add_filter(DiscountFilter::new(0.1));
        // MarkBulkFilter runs only when the predicate is true.
        pipeline.add_valve(AtLeastPredicate::new("qty", 10.0), MarkBulkFilter);
        // A Tap failure is recorded and does not stop the run.
        pipeline.add_tap(AuditTap);
    }
}
