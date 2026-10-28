use crate::payload::Payload;
use crate::step_error::StepError;

/// Hook: sees the lifecycle of a run. Implement the methods that you need;
/// the others do nothing.
///
/// `step` is the label of the step, or `None` for the pipeline itself. A Hook
/// reads the Payload and does not write to it.
pub trait Hook<P = Payload> {
    /// Before a step, or before the pipeline starts (`step` is `None`).
    fn before(&self, _step: Option<&str>, _payload: &P) {}

    /// After a step, or after the pipeline ends (`step` is `None`).
    fn after(&self, _step: Option<&str>, _payload: &P) {}

    /// When a Filter fails: for the step, then for the pipeline (`step` is `None`).
    fn on_error(&self, _step: Option<&str>, _error: &StepError, _payload: &P) {}
}
