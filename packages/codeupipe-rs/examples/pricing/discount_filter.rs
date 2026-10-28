use codeupipe::{Filter, Payload, StepError, Value};

/// A Filter. Its setting is on the instance.
pub struct DiscountFilter {
    rate: f64,
}

impl DiscountFilter {
    pub fn new(rate: f64) -> Self {
        DiscountFilter { rate }
    }
}

impl Filter for DiscountFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let price = payload.get("price").and_then(Value::as_f64).unwrap_or(0.0) * (1.0 - self.rate);
        payload.insert("price", (price * 100.0).round() / 100.0);
        Ok(())
    }
}
