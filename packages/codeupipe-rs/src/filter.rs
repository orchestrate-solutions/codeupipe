use crate::payload::Payload;
use crate::step_error::StepError;

/// Filter: changes the data. A failure is an `Err`, and it stops the run.
///
/// The Filter gets the Payload itself and writes to it in place. It is the
/// only step that can write: the others get `&Payload`.
pub trait Filter<P = Payload> {
    fn call(&self, payload: &mut P) -> Result<(), StepError>;
}
