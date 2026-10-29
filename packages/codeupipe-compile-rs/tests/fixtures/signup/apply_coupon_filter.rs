use codeupipe::{Filter, Payload, StepError};

/// Turns a coupon into a discount, and takes the coupon away.
pub struct ApplyCouponFilter {
    amount: f64,
}

impl ApplyCouponFilter {
    pub fn new(amount: f64) -> Self {
        ApplyCouponFilter { amount }
    }
}

impl Filter for ApplyCouponFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.remove("coupon");
        payload.insert("discount", self.amount);
        Ok(())
    }
}
