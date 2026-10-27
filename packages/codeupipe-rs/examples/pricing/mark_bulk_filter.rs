use codeupipe::{Filter, Payload, StepError};

/// A Filter.
pub struct MarkBulkFilter;

impl Filter for MarkBulkFilter {
    fn call(&self, payload: &mut Payload) -> Result<(), StepError> {
        payload.insert("bulk", true);
        Ok(())
    }
}
