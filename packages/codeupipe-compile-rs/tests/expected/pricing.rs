//! Written by codeupipe-compile from PricingPipeline. Do not edit it: compile again.
//!
//! Plain Rust, with no codeupipe: a struct with one field for each key that
//! the steps use, and one function for each step. It has no State and no
//! Hooks. A Tap failure does not stop the run.
/// The error of a step.
pub type StepError = Box<dyn std::error::Error + Send + Sync>;
/// The data of PricingPipeline: one field for each key that its steps use.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct PricingData {
    /// The key "price".
    pub price: Option<f64>,
    /// The key "qty".
    pub qty: Option<f64>,
    /// The key "bulk".
    pub bulk: Option<bool>,
}
/// DiscountFilter
fn cup_01_discount_filter(payload: &mut PricingData) -> Result<(), StepError> {
    let price = payload.price.unwrap_or(0.0) * (1.0 - 0.1);
    payload.price = Some(::core::convert::Into::into((price * 100.0).round() / 100.0));
    Ok(())
}
/// AtLeastPredicate
fn cup_02_when_at_least_predicate(payload: &PricingData) -> bool {
    payload.qty.unwrap_or(0.0) >= 10.0
}
/// MarkBulkFilter
fn cup_02_mark_bulk_filter(payload: &mut PricingData) -> Result<(), StepError> {
    payload.bulk = Some(::core::convert::Into::into(true));
    Ok(())
}
/// AuditTap
fn cup_03_audit_tap(payload: &PricingData) -> Result<(), StepError> {
    if payload.price.unwrap_or(0.0) < 0.0 {
        return Err("the price is below zero".into());
    }
    Ok(())
}
/// Runs the steps of PricingPipeline, in order, on a copy of `input`.
pub fn run(input: &PricingData) -> Result<PricingData, StepError> {
    let mut payload = input.clone();
    cup_01_discount_filter(&mut payload)?;
    if cup_02_when_at_least_predicate(&payload) {
        cup_02_mark_bulk_filter(&mut payload)?;
    }
    let _ = cup_03_audit_tap(&payload);
    Ok(payload)
}
