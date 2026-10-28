use codeupipe::{Payload, Predicate, Value};

/// get(key) == value, by content; a missing key is null
pub struct EqualsPredicate {
    pub key: String,
    pub value: Value,
}

impl Predicate for EqualsPredicate {
    fn test(&self, payload: &Payload) -> bool {
        payload.get(&self.key).unwrap_or(&Value::Null) == &self.value
    }
}
