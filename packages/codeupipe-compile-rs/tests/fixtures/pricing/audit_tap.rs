use codeupipe::{Payload, StepError, Tap, Value};

/// Reads the price. A negative price is an error of the Tap, which does not stop the run.
pub struct AuditTap;

impl Tap for AuditTap {
    fn observe(&self, payload: &Payload) -> Result<(), StepError> {
        if payload.get("price").and_then(Value::as_f64).unwrap_or(0.0) < 0.0 {
            return Err("the price is below zero".into());
        }
        Ok(())
    }
}
