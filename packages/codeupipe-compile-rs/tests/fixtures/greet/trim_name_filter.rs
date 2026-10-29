use codeupipe::{Filter, Payload, StepError, Value};

/// Trims the name.
pub struct TrimNameFilter;

impl Filter for TrimNameFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let name = payload
            .get("name")
            .and_then(Value::as_str)
            .unwrap_or("")
            .trim()
            .to_string();
        payload.insert("name", name);
        Ok(())
    }
}
