use codeupipe::{Filter, Payload, StepError, Value};

/// insert key = a copy of get(key), or of an empty list, with value added
pub struct AppendFilter {
    pub key: String,
    pub value: Value,
}

impl Filter for AppendFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let mut list = match payload.get(&self.key) {
            None | Some(Value::Null) => Vec::new(),
            Some(Value::List(items)) => items.clone(),
            Some(other) => return Err(format!("'{}' is not a list: {other:?}", self.key).into()),
        };
        list.push(self.value.clone());
        payload.insert(self.key.as_str(), list);
        Ok(())
    }
}
