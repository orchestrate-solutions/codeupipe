use codeupipe::{Filter, StepError};

use crate::order::Order;

/// A Filter. Its setting is on the instance.
pub struct DiscountFilter {
    rate: f64,
}

impl DiscountFilter {
    pub fn new(rate: f64) -> Self {
        DiscountFilter { rate }
    }
}

impl Filter<Order> for DiscountFilter {
    fn call(&self, order: &mut Order) -> Result<(), StepError> {
        order.price = (order.price * (1.0 - self.rate) * 100.0).round() / 100.0;
        Ok(())
    }
}
