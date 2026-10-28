use codeupipe::{Filter, Payload, StepError, Value};

/// insert(key, value) as a statement of its own. A Rust Filter always
/// changes the Payload in place, so this is the same as SetFilter; the case
/// is kept so that every runtime runs it.
pub struct MutateFilter {
    pub key: String,
    pub value: Value,
}

impl Filter for MutateFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert(self.key.as_str(), self.value.clone());
        Ok(())
    }
}
