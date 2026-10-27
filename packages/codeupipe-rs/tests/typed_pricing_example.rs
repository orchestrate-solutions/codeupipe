// The typed example's files, as modules of this test. It is the pricing
// example with an Order struct in place of the Payload, and it must give the
// same result.
#[path = "../examples/typed_pricing/at_least_predicate.rs"]
mod at_least_predicate;
#[path = "../examples/typed_pricing/audit_tap.rs"]
mod audit_tap;
#[path = "../examples/typed_pricing/discount_filter.rs"]
mod discount_filter;
#[path = "../examples/typed_pricing/mark_bulk_filter.rs"]
mod mark_bulk_filter;
#[path = "../examples/typed_pricing/order.rs"]
mod order;
#[path = "../examples/typed_pricing/pricing_pipeline.rs"]
mod pricing_pipeline;

use codeupipe::Pipeline;
use order::Order;
use pricing_pipeline::PricingPipeline;

#[test]
fn a_large_order_gets_the_discount_and_the_bulk_mark() {
    let mut pipeline = Pipeline::named(PricingPipeline);
    let out = pipeline.run(&Order::new(100.0, 12)).unwrap();
    assert_eq!(
        out,
        Order {
            price: 90.0,
            qty: 12,
            bulk: true
        }
    );
    assert_eq!(
        pipeline.state().executed(),
        ["DiscountFilter", "MarkBulkFilter", "AuditTap"]
    );
    assert!(pipeline.state().errors().is_empty());
}

#[test]
fn a_small_order_gets_the_discount_only() {
    let mut pipeline = Pipeline::named(PricingPipeline);
    let out = pipeline.run(&Order::new(100.0, 2)).unwrap();
    assert_eq!(
        out,
        Order {
            price: 90.0,
            qty: 2,
            bulk: false
        }
    );
    assert_eq!(pipeline.state().skipped(), ["MarkBulkFilter"]);
}
