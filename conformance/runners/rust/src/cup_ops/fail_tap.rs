use codeupipe::{Payload, StepError, Tap};

/// return an error
pub struct FailTap {
    pub message: String,
}

impl Tap for FailTap {
    fn observe(&self, _payload: &Payload) -> Result<(), StepError> {
        Err(self.message.clone().into())
    }
}
