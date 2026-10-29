use codeupipe::{Payload, StepError, Tap, Value};

/// Reads the welcome flag, as a counter would.
pub struct CountTap;

impl Tap for CountTap {
    fn observe(&self, payload: &Payload) -> Result<(), StepError> {
        std::hint::black_box(payload.get("welcome").and_then(Value::as_bool));
        Ok(())
    }
}
