use codeupipe::{Filter, Payload, StepError, Value};

/// insert to = get(from), null if missing
pub struct CopyFilter {
    pub from: String,
    pub to: String,
}

impl Filter for CopyFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let value = payload.get(&self.from).cloned().unwrap_or(Value::Null);
        payload.insert(self.to.as_str(), value);
        Ok(())
    }
}
