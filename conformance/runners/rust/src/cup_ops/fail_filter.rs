use codeupipe::{Filter, Payload, StepError};

/// return an error that carries message
pub struct FailFilter {
    pub message: String,
}

impl Filter for FailFilter {
    fn call(&self, _payload: &mut Payload) -> Result<(), StepError> {
        Err(self.message.clone().into())
    }
}
