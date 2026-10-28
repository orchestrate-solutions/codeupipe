// The example's step files, as modules of this test.
#[path = "../examples/pricing/at_least_predicate.rs"]
mod at_least_predicate;
#[path = "../examples/pricing/audit_tap.rs"]
mod audit_tap;
#[path = "../examples/pricing/discount_filter.rs"]
mod discount_filter;
#[path = "../examples/pricing/mark_bulk_filter.rs"]
mod mark_bulk_filter;
#[path = "../examples/pricing/pricing_pipeline.rs"]
mod pricing_pipeline;

use codeupipe::{Map, Payload, Pipeline, Value};
use pricing_pipeline::PricingPipeline;

#[test]
fn a_large_order_gets_the_discount_and_the_bulk_mark() {
    let pipeline = Pipeline::named(PricingPipeline);
    let out = pipeline
        .run(&Payload::from_map(Map::from([
            ("price", 100.0),
            ("qty", 12.0),
        ])))
        .unwrap();
    assert_eq!(
        out.to_dict(),
        Map::from([
            ("price", Value::from(90)),
            ("qty", Value::from(12)),
            ("bulk", Value::from(true))
        ])
    );
    assert_eq!(
        pipeline.state().executed(),
        ["DiscountFilter", "MarkBulkFilter", "AuditTap"]
    );
    assert!(pipeline.state().errors().is_empty());
}

#[test]
fn the_tap_reads_the_payload() {
    use codeupipe::Tap;
    assert!(audit_tap::AuditTap
        .observe(&Payload::from_map(Map::from([("price", 90)])))
        .is_ok());
}

#[test]
fn a_small_order_gets_the_discount_only() {
    let pipeline = Pipeline::named(PricingPipeline);
    let out = pipeline
        .run(&Payload::from_map(Map::from([
            ("price", 100.0),
            ("qty", 2.0),
        ])))
        .unwrap();
    assert_eq!(out.to_dict(), Map::from([("price", 90), ("qty", 2)]));
    assert_eq!(pipeline.state().skipped(), ["MarkBulkFilter"]);
}
