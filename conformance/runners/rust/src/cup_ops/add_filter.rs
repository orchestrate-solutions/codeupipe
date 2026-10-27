use codeupipe::{Filter, Payload, StepError, Value};

/// insert key = get(key, 0) + by
pub struct AddFilter {
    pub key: String,
    pub by: f64,
}

impl Filter for AddFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let n = match payload.get(&self.key) {
            None => 0.0,
            Some(Value::Number(n)) => *n,
            Some(other) => return Err(format!("'{}' is not a number: {other:?}", self.key).into()),
        };
        payload.insert(self.key.as_str(), n + self.by);
        Ok(())
    }
}
