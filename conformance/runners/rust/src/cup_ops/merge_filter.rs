use codeupipe::{Filter, Map, Payload, StepError};

/// merge(Payload(value))
pub struct MergeFilter {
    pub value: Map,
}

impl Filter for MergeFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.merge(&Payload::from_map(self.value.clone()));
        Ok(())
    }
}
