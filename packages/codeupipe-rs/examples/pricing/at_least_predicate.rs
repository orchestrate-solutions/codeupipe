use codeupipe::{Payload, Predicate, Value};

/// A Predicate: asks a yes-or-no question and changes nothing. Its settings
/// are on the instance.
pub struct AtLeastPredicate {
    key: String,
    minimum: f64,
}

impl AtLeastPredicate {
    pub fn new(key: &str, minimum: f64) -> Self {
        AtLeastPredicate {
            key: key.to_string(),
            minimum,
        }
    }
}

impl Predicate for AtLeastPredicate {
    fn test(&self, payload: &Payload) -> bool {
        payload
            .get(&self.key)
            .and_then(Value::as_f64)
            .unwrap_or(0.0)
            >= self.minimum
    }
}
