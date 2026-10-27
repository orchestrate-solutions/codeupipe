use codeupipe::{Payload, StepError, Tap};

/// A Tap: reads the Payload and returns nothing. This one fails every time,
/// to show that a Tap failure is recorded and never stops the run.
pub struct AuditTap;

impl Tap for AuditTap {
    fn observe(&self, _payload: &Payload) -> Result<(), StepError> {
        Err("audit sink is down".into())
    }
}
