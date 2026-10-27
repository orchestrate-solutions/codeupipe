//! cargo run --example typed_pricing: the pricing example with a struct of
//! your own in place of the Payload.
mod at_least_predicate;
mod audit_tap;
mod discount_filter;
mod mark_bulk_filter;
mod order;
mod pricing_pipeline;

use codeupipe::{Pipeline, StepError};

use order::Order;
use pricing_pipeline::PricingPipeline;

fn main() -> Result<(), StepError> {
    let mut pipeline = Pipeline::named(PricingPipeline);
    let result = pipeline.run(&Order::new(100.0, 12))?;

    let state = pipeline.state();
    println!("result:   {result:?}");
    println!("executed: {:?}", state.executed());
    println!("skipped:  {:?}", state.skipped());
    Ok(())
}
