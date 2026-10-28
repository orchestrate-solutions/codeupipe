use codeupipe::{Payload, StepError, Tap};

/// do nothing
pub struct NoopTap;

impl Tap for NoopTap {
    fn observe(&self, _payload: &Payload) -> Result<(), StepError> {
        Ok(())
    }
}
