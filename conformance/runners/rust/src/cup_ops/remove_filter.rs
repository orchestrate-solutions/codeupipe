use codeupipe::{Filter, Payload, StepError};

/// remove(key)
pub struct RemoveFilter {
    pub key: String,
}

impl Filter for RemoveFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.remove(&self.key);
        Ok(())
    }
}
