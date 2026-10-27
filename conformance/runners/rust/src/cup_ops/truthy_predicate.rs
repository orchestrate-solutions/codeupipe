use codeupipe::{Payload, Predicate, Value};

/// get(key) is truthy, as in Python: null, false, 0, "" and an empty list
/// or map are false. A missing key is false.
pub struct TruthyPredicate {
    pub key: String,
}

impl Predicate for TruthyPredicate {
    fn test(&self, payload: &Payload) -> bool {
        match payload.get(&self.key) {
            None | Some(Value::Null) => false,
            Some(Value::Bool(b)) => *b,
            Some(Value::Number(n)) => *n != 0.0,
            Some(Value::String(s)) => !s.is_empty(),
            Some(Value::List(items)) => !items.is_empty(),
            Some(Value::Map(map)) => !map.is_empty(),
        }
    }
}
