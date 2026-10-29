use codeupipe::{Payload, Predicate};

pub struct HasKeyPredicate {
    key: String,
}

impl HasKeyPredicate {
    pub fn new(key: &str) -> Self {
        HasKeyPredicate { key: key.into() }
    }
}

impl Predicate for HasKeyPredicate {
    fn test(&self, payload: &Payload) -> bool {
        payload.has(&self.key)
    }
}
