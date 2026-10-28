use codeupipe::{Filter, Payload, StepError, Value};

/// insert key = value
pub struct SetFilter {
    pub key: String,
    pub value: Value,
}

impl Filter for SetFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert(self.key.as_str(), self.value.clone());
        Ok(())
    }
}
