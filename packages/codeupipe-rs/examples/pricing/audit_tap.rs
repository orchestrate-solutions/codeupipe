use codeupipe::{Payload, StepError, Tap};

/// A Tap: reads the Payload and returns nothing. If it fails, State records
/// the error and the run goes on.
pub struct AuditTap;

impl Tap for AuditTap {
    fn observe(&self, payload: &Payload) -> Result<(), StepError> {
        println!("audit: {:?}", payload.to_dict());
        Ok(())
    }
}
