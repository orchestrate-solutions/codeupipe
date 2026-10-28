//! cargo run --example pricing: run the pipeline with a Hook and show its State.
mod at_least_predicate;
mod audit_tap;
mod discount_filter;
mod mark_bulk_filter;
mod pricing_pipeline;
mod print_steps_hook;

use codeupipe::{Map, Payload, Pipeline, StepError};

use pricing_pipeline::PricingPipeline;
use print_steps_hook::PrintStepsHook;

fn main() -> Result<(), StepError> {
    let mut pipeline = Pipeline::named(PricingPipeline);
    pipeline.use_hook(PrintStepsHook);

    println!("steps:");
    let result = pipeline.run(&Payload::from_map(Map::from([
        ("price", 100.0),
        ("qty", 12.0),
    ])))?;

    let state = pipeline.state();
    let errors: Vec<(&str, String)> = state
        .errors()
        .iter()
        .map(|(label, error)| (label.as_str(), error.to_string()))
        .collect();
    println!("result:   {:?}", result.to_dict());
    println!("executed: {:?}", state.executed());
    println!("skipped:  {:?}", state.skipped());
    println!("errors:   {errors:?}");
    Ok(())
}
