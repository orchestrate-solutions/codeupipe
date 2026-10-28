use codeupipe::{NamedPipeline, Pipeline};

use crate::at_least_predicate::AtLeastPredicate;
use crate::audit_tap::AuditTap;
use crate::discount_filter::DiscountFilter;
use crate::mark_bulk_filter::MarkBulkFilter;
use crate::order::Order;

/// The pricing pipeline of `examples/pricing`, carrying an Order.
pub struct PricingPipeline;

impl NamedPipeline<Order> for PricingPipeline {
    fn add_steps(&self, pipeline: &mut Pipeline<Order>) {
        pipeline.add_filter(DiscountFilter::new(0.1));
        // MarkBulkFilter runs only when the predicate is true.
        pipeline.add_valve(AtLeastPredicate::new(10), MarkBulkFilter);
        // A Tap only reads. If it fails, State records the error and the run goes on.
        pipeline.add_tap(AuditTap);
    }
}
