use codeupipe::{Filter, Payload, StepError};

/// insert to = has(key)
pub struct HasFilter {
    pub key: String,
    pub to: String,
}

impl Filter for HasFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        let has = payload.has(&self.key);
        payload.insert(self.to.as_str(), has);
        Ok(())
    }
}
