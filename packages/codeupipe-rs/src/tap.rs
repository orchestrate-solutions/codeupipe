use crate::payload::Payload;
use crate::step_error::StepError;

/// Tap: reads the data as it goes by. It does not write to the Payload.
/// A Tap failure is recorded in State and never stops the run.
pub trait Tap {
    fn observe(&self, payload: &Payload) -> Result<(), StepError>;
}
